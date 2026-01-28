#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { MercadonaClient } from "./mercadona-client.js";
import { calculateSmartCart } from "./smart-cart.js";
import fs from 'fs-extra';
import path from 'path';
import os from 'os';

const server = new McpServer({
    name: "mercadona-mcp",
    version: "1.0.0",
});

let client: MercadonaClient;

try {
    client = new MercadonaClient();
} catch (e) {
    console.error("Warning: Client initialization failed:", e);
}

function checkClient() {
    if (!client) {
        try {
            client = new MercadonaClient();
        } catch {
            throw new Error("MercadonaClient is not initialized. Please run the 'login' tool.");
        }
    }
}

function checkAuth() {
    checkClient();
    if (!client.isLoggedIn) {
        throw new Error("User is NOT authenticated. Please run the 'login' tool to authenticate with Mercadona.");
    }
}

// Tools

server.tool(
    "get_status",
    "Check if the agent is currently logged in and view active configuration (postal code, warehouse).",
    {},
    async () => {
        checkClient();
        return {
            content: [{
                type: "text",
                text: JSON.stringify({
                    authenticated: client.isLoggedIn,
                    postal_code: client.currentPostalCode || "Not set",
                    warehouse_id: client.currentWarehouseId,
                    message: client.isLoggedIn
                        ? "You are logged in and ready to shop."
                        : "You are NOT logged in. Use the 'login' tool to authenticate."
                }, null, 2)
            }]
        };
    }
);


server.tool(
    "login",
    "Returns instructions on how to log in to Mercadona.",
    {},
    async () => {
        return {
            content: [{
                type: "text",
                text:
                    "STRICTLY FOLLOW THIS PROCEDURE to log in:\n" +
                    "1. STEP 1: Call 'browser_subagent' to navigate to 'https://tienda.mercadona.es/?authenticate-user='.\n" +
                    "2. CRITICAL: The subagent MUST finish its task after navigation. Do NOT keep the subagent running/polling.\n" +
                    "3. STEP 2: Call 'notify_user' to ask the user to log in manually in the now-opened browser.\n" +
                    "4. STEP 3: After the user confirms login, call 'browser_subagent' AGAIN with this EXACT task:\n" +
                    "   'Retrieve MO-user from LocalStorage and __mo_da cookie. Parse postal_code and warehouse_id from the cookie (URL-decode first). Write directly to ~/.mercadona_auth.json with structure: {\"local_storage\": {\"MO-user\": \"<stringified_mo_user>\"}, \"location\": {\"postal_code\": \"<value>\", \"warehouse_id\": \"<value>\"}, \"cookies\": {}}. DO NOT report credentials back - only confirm file write success.'\n" +
                    "5. The subagent will write the file and check 'get_status' to confirm success.\n" +
                    "6. Confirm to the user that login credentials have been saved.\n"
            }]
        };
    }
);

server.tool(
    "set_credentials",
    "Save the Mercadona session credentials.",
    {
        mo_user: z.record(z.any()).describe("The JSON object found in LocalStorage under 'MO-user'")
    },
    async ({ mo_user }) => {
        if (!client) client = new MercadonaClient();
        if (client.saveAuth(mo_user)) {
            return { content: [{ type: "text", text: "Credentials saved successfully." }] };
        }
        return { content: [{ type: "text", text: "Failed to save credentials." }] };
    }
);

server.tool(
    "set_location",
    "Save the location (Warehouse ID and Postal Code).",
    {
        postal_code: z.string().describe("5-digit postal code"),
        warehouse_id: z.string().describe("Warehouse ID")
    },
    async ({ postal_code, warehouse_id }) => {
        if (!client) client = new MercadonaClient();
        if (client.saveAuth(undefined, { postal_code, warehouse_id })) {
            return { content: [{ type: "text", text: `Location saved: ${postal_code} (Warehouse ${warehouse_id}).` }] };
        }
        return { content: [{ type: "text", text: "Failed to save location." }] };
    }
);

server.tool(
    "search_products",
    "Search for products in Mercadona.",
    { query: z.string() },
    async ({ query }) => {
        checkClient();
        const results = await client.searchProducts(query);
        const output = results.map(p => ({
            id: p.id,
            name: p.display_name,
            price: p.price_instructions?.unit_price || 'N/A',
            packaging: p.packaging
        }));
        return { content: [{ type: "text", text: JSON.stringify(output, null, 2) }] };
    }
);

server.tool(
    "get_product_details",
    "Get detailed information about a specific product.",
    { product_id: z.string() },
    async ({ product_id }) => {
        checkClient();
        const details = await client.getProductDetails(product_id);
        if (!details) return { content: [{ type: "text", text: "Product not found." }], isError: true };
        return { content: [{ type: "text", text: JSON.stringify(details, null, 2) }] };
    }
);

server.tool(
    "get_cart",
    "Get the current shopping cart status.",
    {},
    async () => {
        checkAuth();
        const cart = await client.getCart();
        if (!cart) return { content: [{ type: "text", text: "Failed to fetch cart." }], isError: true };

        const items = cart.lines.map(line => ({
            id: line.product?.id,
            name: line.product?.display_name,
            quantity: line.quantity,
            unit_price: line.product?.price_instructions?.unit_price
        }));

        return {
            content: [{
                type: "text", text: JSON.stringify({
                    cart_id: cart.id,
                    total: cart.summary.total,
                    items
                }, null, 2)
            }]
        };
    }
);

server.tool(
    "add_to_cart",
    "Add a product to the cart.",
    {
        product_id: z.string(),
        quantity: z.number().default(1)
    },
    async ({ product_id, quantity }) => {
        checkAuth();
        if (await client.addToCart(product_id, quantity)) {
            return { content: [{ type: "text", text: `Successfully added product ${product_id} (Qty: ${quantity}) to cart.` }] };
        }
        return { content: [{ type: "text", text: "Failed to add product to cart." }], isError: true };
    }
);

server.tool(
    "add_to_cart_bulk",
    "Add multiple products to the cart at once.",
    {
        items: z.array(z.object({
            product_id: z.string(),
            quantity: z.number().optional().default(1)
        }))
    },
    async ({ items }) => {
        checkAuth();
        if (!items || items.length === 0) {
            return { content: [{ type: "text", text: "No items provided." }], isError: true };
        }

        // Map simplified items to required structure if needed, but client handles it
        // The zod schema ensures we get objects with product_id
        // We cast to any because zod inference vs explicit type in client
        if (await client.addToCartBulk(items as any)) {
            const totalQty = items.reduce((sum, item) => sum + (item.quantity || 1), 0);
            return {
                content: [{
                    type: "text", text:
                        `Successfully added ${items.length} product(s) with total quantity of ${totalQty} to cart.\n\n` +
                        "INSTRUCTION TO ORCHESTRATOR: Please invite the user to check their cart at https://tienda.mercadona.es/"
                }]
            };
        }
        return { content: [{ type: "text", text: "Failed to add products to cart." }], isError: true };
    }
);

server.tool(
    "remove_from_cart",
    "Remove a product from the cart completely.",
    { product_id: z.string() },
    async ({ product_id }) => {
        checkAuth();
        if (await client.removeFromCart(product_id)) {
            return { content: [{ type: "text", text: `Successfully removed product ${product_id} from cart.` }] };
        }
        return { content: [{ type: "text", text: "Failed to remove product from cart." }], isError: true };
    }
);

server.tool(
    "clear_cart",
    "Clear all items from the shopping cart.",
    {},
    async () => {
        checkAuth();
        if (await client.clearCart()) {
            return { content: [{ type: "text", text: "Successfully cleared the cart." }] };
        }
        return { content: [{ type: "text", text: "Failed to clear the cart." }], isError: true };
    }
);

server.tool(
    "list_recent_orders",
    "List the most recent orders.",
    { limit: z.number().default(100) },
    async ({ limit }) => {
        checkAuth();
        const orders = await client.listOrders(limit);
        return { content: [{ type: "text", text: JSON.stringify(orders, null, 2) }] };
    }
);

server.tool(
    "calculate_smart_cart",
    "Analyzes order history and generates smart shopping cart recommendations.",
    {},
    async () => {
        checkAuth();
        const result = await calculateSmartCart(client);
        return { content: [{ type: "text", text: result }] };
    }
);

// Resources

server.resource(
    "cart",
    "mercadona://cart",
    async (uri) => {
        checkClient(); // Cart resource might be accessed to check state, but better to be safe
        const cart = await client.getCart();
        return {
            contents: [{
                uri: uri.href,
                text: cart ? JSON.stringify(cart, null, 2) : JSON.stringify({ error: "Not authenticated or empty cart" })
            }]
        };
    }
);

server.resource(
    "smart_cart",
    "mercadona://smart_cart",
    async (uri) => {
        const outputPath = path.join(os.homedir(), 'smart_cart_calculation.json');
        if (!fs.existsSync(outputPath)) {
            return {
                contents: [{ uri: uri.href, text: JSON.stringify({ error: "No smart cart calculation found." }) }]
            };
        }
        const data = await fs.readJson(outputPath);
        return {
            contents: [{
                uri: uri.href,
                text: `${JSON.stringify(data, null, 2)}\n\nINSTRUCTION TO ORCHESTRATOR: Please present the 'items' from the JSON data above as a pretty markdown table with columns: ID, Name, Suggested Qty, Frequency, and Reason.`
            }]
        };
    }
);

server.resource(
    "recent_orders",
    "mercadona://recent_orders",
    async (uri) => {
        checkClient();
        const orders = await client.listOrders(20);
        return {
            contents: [{ uri: uri.href, text: orders ? JSON.stringify(orders, null, 2) : "[]" }]
        };
    }
);

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}

main().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
});
