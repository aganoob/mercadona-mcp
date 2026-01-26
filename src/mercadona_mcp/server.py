from mcp.server.fastmcp import FastMCP
from .mercadona_client import MercadonaClient
import json

# Initialize Server
mcp = FastMCP("mercadona-mcp")

# Initialize Client
# We ensure the client is ready. If auth fails, tools will error out gracefully.
try:
    client = MercadonaClient()
except Exception as e:
    print(f"Warning: Client initialization failed: {e}")
    client = None

def check_client():
    if not client:
        raise RuntimeError("MercadonaClient is not initialized. Check auth_config.json.")

@mcp.tool()
def get_login_instructions():
    """
    Returns instructions on how to log in to Mercadona and retrieve the session token.
    Use this when the user wants to log in or when authentication fails.
    """
    return (
        "To log in to Mercadona:\n"
        "1. Open 'https://tienda.mercadona.es' in a browser.\n"
        "2. Log in manually with your credentials.\n"
        "3. Once logged in, open Developer Tools -> Application -> Cookies.\n"
        "4. Find the cookie named '__mo_da'. It contains your warehouse and postal code (e.g., %7B%22warehouse%22%3A%224115%22%2C%22postalCode%22%3A%2246001%22%7D).\n"
        "5. Also find the value of 'MO-user' in LocalStorage (Application -> storage -> Local Storage).\n"
        "6. Call the 'set_credentials' tool with the MO-user value.\n"
        "7. Call the 'set_location' tool with the postal code and warehouse ID from '__mo_da'."
    )

@mcp.tool()
def set_credentials(mo_user: dict):
    """
    Save the Mercadona session credentials.
    Args:
        mo_user: The JSON object found in LocalStorage under the key 'MO-user'. 
                 It should contain 'token' and 'uuid'.
    """
    # Ensure client exists
    c = client
    if not c:
        try:
             c = MercadonaClient()
        except:
             return "Client initialization failed."

    if c.save_auth(mo_user_data=mo_user):
        return "Credentials saved successfully."
    else:
        return "Failed to save credentials."

@mcp.tool()
def set_location(postal_code: str, warehouse_id: str):
    """
    Save the location (Warehouse ID and Postal Code) for the session.
    Vital for correct product search and availability.
    Args:
        postal_code: The 5-digit postal code (e.g., '46001').
        warehouse_id: The warehouse ID (e.g., '4115').
    """
    # Ensure client exists
    c = client
    if not c:
        try:
             c = MercadonaClient()
        except:
             return "Client initialization failed."

    if c.save_auth(location_data={"postal_code": postal_code, "warehouse_id": warehouse_id}):
        return f"Location saved: {postal_code} (Warehouse {warehouse_id})."
    else:
        return "Failed to save location."

@mcp.tool()
def search_products(query: str):
    """
    Search for products in Mercadona.
    Returns a list of products with ID, Name, and Price.
    """
    check_client()
    results = client.search_products(query)
    # Return simplified list for the LLM
    output = []
    for p in results:
        price = p.get('price_instructions', {}).get('unit_price', 'N/A')
        output.append({
            "id": p['id'],
            "name": p['display_name'],
            "price": price,
            "packaging": p.get('packaging')
        })
    return output

@mcp.tool()
def get_product_details(product_id: str):
    """
    Get detailed information about a specific product.
    Includes status, packaging, and extra info.
    """
    check_client()
    return client.get_product_details(product_id)

@mcp.tool()
def get_cart():
    """
    Get the current shopping cart status.
    Returns the Cart ID, Version, Total price, and a list of items.
    """
    check_client()
    cart = client.get_cart()
    if not cart:
        return "Failed to fetch cart or cart is empty/invalid."
    
    items = []
    for line in cart.get("lines", []):
        p = line.get("product", {})
        items.append({
            "id": p.get("id"),
            "name": p.get("display_name"),
            "quantity": line.get("quantity"),
            "unit_price": p.get("price_instructions", {}).get("unit_price")
        })

    return {
        "cart_id": cart.get("id"),
        "total": cart.get("summary", {}).get("total"),
        "items": items
    }

@mcp.tool()
def add_to_cart(product_id: str, quantity: int = 1):
    """
    Add a product to the cart.
    Args:
        product_id: The ID of the product to add.
        quantity: The number of units to add (default 1).
    """
    check_client()
    if client.add_to_cart(product_id, quantity):
        return f"Successfully added product {product_id} (Qty: {quantity}) to cart."
    else:
        return "Failed to add product to cart."

@mcp.tool()
def remove_from_cart(product_id: str):
    """Remove a product from the cart completely."""
    check_client()
    if client.remove_from_cart(product_id):
        return f"Successfully removed product {product_id} from cart."
    else:
        return "Failed to remove product from cart."

@mcp.tool()
def list_recent_orders(limit: int = 5):
    """List the most recent orders placed by the user."""
    check_client()
    return client.list_orders(limit)

@mcp.resource("mercadona://cart")
def resource_cart() -> str:
    """Real-time view of the shopping cart in JSON format."""
    check_client()
    cart = client.get_cart()
    return json.dumps(cart, indent=2) if cart else "{}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
