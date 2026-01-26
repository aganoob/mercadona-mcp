from src.mercadona_client import MercadonaClient
import sys

def main():
    print("Initializing MercadonaClient...")
    try:
        client = MercadonaClient()
        print("Auth loaded successfully.")
    except Exception as e:
        print(f"FAILED to load client: {e}")
        sys.exit(1)

    print("\n--- Testing Search ---")
    results = client.search_products("leche")
    if results:
        print(f"Found {len(results)} products for 'leche'.")
        print(f"Top result: {results[0]['display_name']} ({results[0]['id']})")
    else:
        print("No products found (or search failed).")

    print("\n--- Testing Cart Fetch ---")
    cart = client.get_cart()
    if cart:
        print(f"Cart ID: {cart.get('id')}")
        print(f"Items: {len(cart.get('lines', []))}")
    else:
        print("Failed to fetch cart.")

    print("\n--- Testing Order List ---")
    orders = client.list_orders(limit=1)
    if orders:
        print(f"Found {len(orders)} orders.")
        print(f"Latest Order ID: {orders[0]['id']}")
    else:
        print("No orders found.")

if __name__ == "__main__":
    main()
