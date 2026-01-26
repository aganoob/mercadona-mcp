from mcp.server.fastmcp import FastMCP
from .mercadona_client import MercadonaClient
import sys
import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import statistics

# Initialize Server
mcp = FastMCP("mercadona-mcp")

# Initialize Client
# We ensure the client is ready. If auth fails, tools will error out gracefully.
try:
    client = MercadonaClient()
except Exception as e:
    sys.stderr.write(f"Warning: Client initialization failed: {e}\n")
    client = None

def check_client():
    if not client:
        raise RuntimeError("MercadonaClient is not initialized. Please run the 'login' tool to perform login and save credentials.")

@mcp.tool()
def login():
    """
    Returns instructions on how to log in to Mercadona and retrieve the session token.
    Use this when the user wants to log in or when authentication fails.
    """
    return (
        "STRICTLY FOLLOW THIS PROCEDURE to log in:\n"
        "1. STEP 1: Call 'browser_subagent' to navigate to 'https://tienda.mercadona.es/?authenticate-user='.\n"
        "2. CRITICAL: The subagent MUST finish its task after navigation. Do NOT keep the subagent running/polling.\n"
        "3. STEP 2: Call 'notify_user' to ask the user to log in manually in the now-opened browser.\n"
        "4. STEP 3: After the user confirms login, call 'browser_subagent' AGAIN with this EXACT task:\n"
        "   'Retrieve MO-user from LocalStorage and __mo_da cookie. Parse postal_code and warehouse_id from the cookie (URL-decode first). Write directly to ~/.mercadona_auth.json with structure: {\"local_storage\": {\"MO-user\": \"<stringified_mo_user>\"}, \"location\": {\"postal_code\": \"<value>\", \"warehouse_id\": \"<value>\"}, \"cookies\": {}}. DO NOT report credentials back - only confirm file write success.'\n"
        "5. The subagent will write the file and report only confirmation (not the actual credentials).\n"
        "6. Confirm to the user that login credentials have been saved.\n"
        "\n"
        "⚠️ CRITICAL SECURITY REQUIREMENT:\n"
        "- User credentials (tokens, UUIDs, passwords) must NEVER be explicitly shown in responses\n"
        "- NEVER display the contents of authentication files or tokens\n"
        "- Only confirm successful save/write operations\n"
        "- If debugging is needed, only show confirmation messages, NOT actual credential values"
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
    Args:
        query: Product search term or keywords (e.g., 'leche', 'pan', 'tomates').
               Can be partial names, brand names, or product categories.
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
    Args:
        product_id: The unique product identifier (e.g., '12345').
                    Can be obtained from search_products results.
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
def add_to_cart_bulk(items: list):
    """
    Add multiple products to the cart at once.
    This is useful for adding items from smart cart or multiple products efficiently.
    Args:
        items: List of items to add. Each item should be a dict with:
               - product_id (str, required): The ID of the product to add
               - quantity (int, optional): The number of units to add (default 1)
               Example: [{"product_id": "12345", "quantity": 2}, {"product_id": "67890", "quantity": 1}]
    """
    check_client()
    if not items:
        return "No items provided to add to cart."
    
    if client.add_to_cart_bulk(items):
        total_items = len(items)
        total_qty = sum(item.get("quantity", 1) for item in items)
        return f"Successfully added {total_items} product(s) with total quantity of {total_qty} to cart."
    else:
        return "Failed to add products to cart."

@mcp.tool()
def remove_from_cart(product_id: str):
    """
    Remove a product from the cart completely.
    Args:
        product_id: The unique product identifier to remove from the cart.
                    All quantities of this product will be removed.
    """
    check_client()
    if client.remove_from_cart(product_id):
        return f"Successfully removed product {product_id} from cart."
    else:
        return "Failed to remove product from cart."

@mcp.tool()
def clear_cart():
    """
    Clear all items from the shopping cart.
    This empties the entire cart, removing all products.
    """
    check_client()
    if client.clear_cart():
        return "Successfully cleared the cart."
    else:
        return "Failed to clear the cart."

@mcp.tool()
def list_recent_orders(limit: int = 100):
    """
    List the most recent orders placed by the user.
    Args:
        limit: Maximum number of orders to retrieve (default: 100).
               Higher values will take longer to fetch.
    """
    check_client()
    return client.list_orders(limit)

@mcp.tool()
def calculate_smart_cart():
    """
    Analyzes order history and generates smart shopping cart recommendations.
    Returns suggested items based on purchase frequency and intervals.
    Results are saved to ~/smart_cart_calculation.json.
    """
    check_client()
    
    # Fetch all orders with details
    orders = client.list_orders(limit=100)  # Get up to 100 recent orders
    
    if not orders:
        return "No order history found."
    
    # Filter orders from last year
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
    product_stats = {}
    
    for order in orders:
        order_date_str = order.get("start_date")
        if not order_date_str:
            continue
            
        try:
            order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
        except:
            continue
            
        if order_date < cutoff_date:
            continue
        
        # Get order details
        order_id = order.get("id")
        order_lines = client.get_order_details(order_id)
        
        if not order_lines:
            continue
            
        for line in order_lines:
            pid = line.get("product_id")
            if not pid:
                continue
                
            product = line.get("product", {})
            pname = product.get("display_name", "Unknown Product")
            qty = line.get("ordered_quantity", 0)
            
            if pid not in product_stats:
                product_stats[pid] = {
                    "id": pid,
                    "name": pname,
                    "dates": [],
                    "qtys": []
                }
            
            product_stats[pid]["dates"].append(order_date)
            product_stats[pid]["qtys"].append(qty)
    
    # Calculate recommendations
    recommendations = []
    now = datetime.now(timezone.utc)
    
    for pid, stats in product_stats.items():
        dates = sorted(stats["dates"])
        if not dates:
            continue
            
        last_purchased = dates[-1]
        days_since_last = (now - last_purchased).days
        count = len(dates)
        total_qty = sum(stats["qtys"])
        avg_qty = total_qty / count if count > 0 else 1
        
        # Calculate intervals
        intervals = []
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i-1]).days
            intervals.append(delta)
        
        avg_interval = statistics.mean(intervals) if intervals else 30
        
        # Recommendation logic: bought 3+ times and due for replenishment
        if count >= 3:
            threshold = max(avg_interval * 0.6, 4)
            if days_since_last >= threshold:
                suggested_qty = round(avg_qty)
                if suggested_qty < 1:
                    suggested_qty = 1
                    
                recommendations.append({
                    "id": pid,
                    "name": stats["name"],
                    "reason": f"Regular replenishment (Last: {days_since_last}d ago, Avg Int: {avg_interval:.1f}d)",
                    "suggested_qty": int(suggested_qty),
                    "frequency": count
                })
    
    # Sort by frequency
    recommendations.sort(key=lambda x: x["frequency"], reverse=True)
    
    # Save results
    output = {
        "generated_at": now.isoformat(),
        "items": recommendations,
        "discovery": []
    }
    
    output_path = os.path.expanduser("~/smart_cart_calculation.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    return f"Smart cart calculated with {len(recommendations)} recommendations. Saved to {output_path}"

@mcp.resource("mercadona://cart")
def resource_cart() -> str:
    """Real-time view of the shopping cart in JSON format."""
    check_client()
    cart = client.get_cart()
    return json.dumps(cart, indent=2) if cart else "{}"

@mcp.resource("mercadona://smart_cart")
def resource_smart_cart() -> str:
    """View the last smart cart calculation results."""
    output_path = os.path.expanduser("~/smart_cart_calculation.json")
    
    if not os.path.exists(output_path):
        return json.dumps({"error": "No smart cart calculation found. Run calculate_smart_cart tool first."}, indent=2)
    
    with open(output_path, "r") as f:
        data = json.load(f)
    
    return json.dumps(data, indent=2)

@mcp.resource("mercadona://recent_orders")
def resource_recent_orders() -> str:
    """View recent orders (last 20)."""
    check_client()
    orders = client.list_orders(limit=20)
    return json.dumps(orders, indent=2) if orders else "[]"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
