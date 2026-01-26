import os
import sys
import json
import time
from mercadona_mcp.mercadona_client import MercadonaClient

def run_test_scenario():
    print("=== Testing Scenario: The Morning Milk Run ===")
    
    # 1. Initialization
    print("\n[1] Initializing Client...")
    client = MercadonaClient()
    
    if not client.token:
        print("❌ Error: Valid token not found. Please populate auth_config.json/MERCADONA_AUTH_FILE.")
        return
    
    print(f"✅ Client Loaded.")
    print(f"👉 Token (Masked): {client.token[:5]}...")
    print(f"👉 UUID: {client.uuid}")
    print(f"👉 Location: {client.postal_code} (Warehouse {client.warehouse_id})")
    print(f"👉 Algolia URL: {client.algolia_url}")

    # 2. Product Search
    search_query = "Leche"
    print(f"\n[2] Searching for '{search_query}'...")
    products = client.search_products(search_query)
    
    if not products:
        print("❌ Error: No products found. Check Algolia config.")
        return

    print(f"✅ Found {len(products)} products.")
    target_product = products[0]
    print(f"👉 Target Product: {target_product.get('display_name')} (ID: {target_product.get('id')})")
    
    # 3. Cart Inspection
    print("\n[3] Inspecting Cart (Pre-Add)...")
    cart_pre = client.get_cart()
    if not cart_pre:
        print("❌ Error: Failed to fetch cart.")
        return
    
    initial_items = len(cart_pre.get('lines', []))
    print(f"✅ Current Cart Items: {initial_items}")

    # Safety Check
    print("\n⚠️  WARNING: This script involves modifying your REAL shopping cart.")
    print(f"   Action: Add and then Remove 1 unit of '{target_product.get('display_name')}'")
    confirm = input("   Proceed? (y/n): ")
    if confirm.lower() != 'y':
        print("⏹️  Test Checkpoint: Aborted by user.")
        return

    # 4. Add to Cart
    print(f"\n[4] Adding to Cart...")
    product_id = target_product.get('id')
    success = client.add_to_cart(product_id, 1)
    
    if success:
        print(f"✅ Added product {product_id} successfully.")
    else:
        print(f"❌ Failed to add product.")
        return

    # Verify Addition
    cart_mid = client.get_cart()
    mid_items = len(cart_mid.get('lines', []))
    print(f"👉 Cart Item Count: {initial_items} -> {mid_items}")
    
    if mid_items <= initial_items:
         print("❌ Verification Failed: Item count did not increase.")
         # Try to continue to cleanup anyway? No, might delete something else if logic is weird.
         return

    # 5. Remove from Cart
    print(f"\n[5] Removing from Cart (Cleanup)...")
    # Wait a sec to be nice to the API
    time.sleep(1)
    
    success_remove = client.remove_from_cart(product_id)
    if success_remove:
        print(f"✅ Removed product {product_id} successfully.")
    else:
        print(f"❌ Failed to remove product.")
        return

    # Verify Removal
    cart_post = client.get_cart()
    post_items = len(cart_post.get('lines', []))
    print(f"👉 Cart Item Count: {mid_items} -> {post_items}")
    
    if post_items != initial_items:
        print("⚠️ Warning: Post-cleanup item count matches initial count? " + ("Yes" if post_items == initial_items else "No"))
    
    print("\n=== Scenario Completed Successfully ===")

if __name__ == "__main__":
    run_test_scenario()
