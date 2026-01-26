import json
import requests
import os
from typing import Optional, Dict, List, Any

class MercadonaClient:
    ALGOLIA_APP_ID = "7UZJKL1DJ0"
    ALGOLIA_API_KEY = "9d8f2e39e90df472b4f2e559a116fe17" # Public Key from Swagger/Frontend
    BASE_URL = "https://tienda.mercadona.es/api"

    def __init__(self, auth_file: Optional[str] = None):
        self.auth_file = auth_file or os.getenv("MERCADONA_AUTH_FILE", os.path.expanduser("~/.mercadona_auth.json"))
        self.token = None
        self.uuid = None
        self.warehouse_id = "4115" # Default to Valencia
        self.postal_code = None
        self.load_auth()

    @property
    def algolia_url(self) -> str:
        return f"https://7UZJKL1DJ0-dsn.algolia.net/1/indexes/products_prod_{self.warehouse_id}_es/query"

    @property
    def common_params(self) -> str:
        return f"?lang=es&wh={self.warehouse_id}"

    def load_auth(self):
        """Loads authentication token, UUID, and location from local config file."""
        if not os.path.exists(self.auth_file):
            print(f"Auth file {self.auth_file} not found. Using defaults.")
            return
        
        try:
            with open(self.auth_file, "r") as f:
                auth_config = json.load(f)
                
                # Load MO-user (Token & UUID)
                if "local_storage" in auth_config and "MO-user" in auth_config["local_storage"]:
                    mo_user_str = auth_config["local_storage"]["MO-user"]
                    # It might be a stringified JSON or just a dict depending on how it was saved
                    if isinstance(mo_user_str, str):
                        try:
                            mo_user = json.loads(mo_user_str)
                        except json.JSONDecodeError:
                            print("Error decoding MO-user string")
                            mo_user = {}
                    else:
                        mo_user = mo_user_str
                    
                    self.token = mo_user.get("token")
                    self.uuid = mo_user.get("uuid")

                # Load Location (Warehouse & Postal Code)
                # We look in a custom "location" key or infer from cookies if previously saved there
                if "location" in auth_config:
                    self.postal_code = auth_config["location"].get("postal_code")
                    self.warehouse_id = auth_config["location"].get("warehouse_id", "4115")
                
                # Check cookies for __mo_da if location is missing
                elif "cookies" in auth_config and "__mo_da" in auth_config["cookies"]:
                    try:
                        mo_da_val = auth_config["cookies"]["__mo_da"]
                        # It might be URL encoded or just raw JSON string
                        # Simple retrieval if it looks like JSON
                        if "{" in mo_da_val:
                            mo_da = json.loads(mo_da_val)
                            self.warehouse_id = mo_da.get("warehouse", self.warehouse_id)
                            self.postal_code = mo_da.get("postalCode", self.postal_code)
                    except Exception as e:
                       print(f"Failed to parse __mo_da cookie: {e}")

        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to load auth from {self.auth_file}: {e}")

    def save_auth(self, mo_user_data: Dict[str, Any] = None, location_data: Dict[str, str] = None) -> bool:
        """Saves auth and/or location data to the config file."""
        try:
            # Load existing first to preserve other keys
            current_config = {}
            if os.path.exists(self.auth_file):
                with open(self.auth_file, "r") as f:
                    try:
                        current_config = json.load(f)
                    except json.JSONDecodeError:
                        pass
            
            # Update MO-user if provided
            if mo_user_data:
                if "local_storage" not in current_config:
                    current_config["local_storage"] = {}
                # Ensure we store it as a string if that's the convention, or simple dict. 
                # The previous code expected json.loads on read, so we stick to stringified JSON for MO-user to match browser localStorage format.
                current_config["local_storage"]["MO-user"] = json.dumps(mo_user_data)
                
                # Update in-memory
                self.token = mo_user_data.get("token")
                self.uuid = mo_user_data.get("uuid")

            # Update Location if provided
            if location_data:
                current_config["location"] = {
                    "postal_code": location_data.get("postal_code"),
                    "warehouse_id": location_data.get("warehouse_id")
                }
                # Update in-memory
                self.postal_code = location_data.get("postal_code")
                if location_data.get("warehouse_id"):
                    self.warehouse_id = location_data.get("warehouse_id")

            with open(self.auth_file, "w") as f:
                json.dump(current_config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save auth: {e}")
            return False

    @property
    def headers(self) -> Dict[str, str]:
        if not self.token:
            self.load_auth()
        return {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }

    def search_products(self, query: str) -> List[Dict[str, Any]]:
        """Searches for products using Algolia."""
        headers = {
            "x-algolia-application-id": self.ALGOLIA_APP_ID,
            "x-algolia-api-key": self.ALGOLIA_API_KEY,
            "Content-Type": "application/json"
        }
        # Algolia payload
        payload = {
            "query": query,
            # We can optionally pass userToken if we have it, helps with personalization but not strictly required
            # "userToken": self.uuid 
        }
        
        try:
            resp = requests.post(self.algolia_url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                # Filter unavailable products
                return [h for h in hits if h.get("published") and not h.get("unavailable_from")]
            else:
                print(f"Search error: {resp.status_code} {resp.text}")
                return []
        except Exception as e:
            print(f"Search exception: {e}")
            return []

    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetches detailed information for a specific product."""
        url = f"{self.BASE_URL}/products/{product_id}/"
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            print(f"Get product details error: {e}")
            return None

    def get_cart(self) -> Optional[Dict[str, Any]]:
        """Retrieves the current shopping cart."""
        url = f"{self.BASE_URL}/customers/{self.uuid}/cart/{self.common_params}"
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"Get cart error: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            print(f"Get cart exception: {e}")
            return None

    def update_cart_items(self, items: List[Dict[str, Any]]) -> bool:
        """
        Updates the cart with the provided list of items (lines).
        Note: This replaces the entire cart content.
        items format: [{"product_id": "123", "quantity": 1}, ...]
        """
        current_cart = self.get_cart()
        if not current_cart:
            return False

        url = f"{self.BASE_URL}/customers/{self.uuid}/cart/{self.common_params}"
        payload = {
            "id": current_cart["id"],
            "version": current_cart["version"],
            "lines": items
        }
        
        try:
            resp = requests.put(url, json=payload, headers=self.headers)
            if resp.status_code in [200, 201]:
                return True
            else:
                print(f"Update cart error: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            print(f"Update cart exception: {e}")
            return False

    def add_to_cart(self, product_id: str, quantity: int = 1) -> bool:
        """Adds an item to the existing cart (merges with existing)."""
        current_cart = self.get_cart()
        if not current_cart:
            return False

        lines_map = {}
        for line in current_cart.get("lines", []):
            pid = line["product"]["id"]
            lines_map[pid] = {
                "product_id": pid,
                "quantity": line["quantity"]
            }
        
        # Add or update
        if product_id in lines_map:
            lines_map[product_id]["quantity"] += quantity
        else:
            lines_map[product_id] = {
                "product_id": product_id,
                "quantity": quantity
            }
            
        return self.update_cart_items(list(lines_map.values()))

    def remove_from_cart(self, product_id: str) -> bool:
        """Removes an item from the cart."""
        current_cart = self.get_cart()
        if not current_cart:
            return False

        lines = []
        for line in current_cart.get("lines", []):
            pid = line["product"]["id"]
            if pid != product_id:
                lines.append({
                    "product_id": pid,
                    "quantity": line["quantity"]
                })
        
        return self.update_cart_items(lines)

    def list_orders(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Lists recent orders."""
        url = f"{self.BASE_URL}/customers/{self.uuid}/orders/"
        orders = []
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                return results[:limit]
            return []
        except Exception as e:
            print(f"List orders error: {e}")
            return []

    def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Gets details (lines) of a specific past order."""
        # Note: 'prepared' lines are for delivered orders.
        url = f"{self.BASE_URL}/customers/{self.uuid}/orders/{order_id}/lines/prepared/"
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return resp.json().get("results", [])
            return None
        except Exception:
            return None
