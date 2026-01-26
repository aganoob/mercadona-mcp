# Mercadona MCP Server

An **MCP Server** for the [Mercadona Online Store](https://tienda.mercadona.es).
This server allows AI assistants (like Claude) to search for products, manage your shopping cart, and view your order history.

## Features
*   **Product Search**: Search for products (via Algolia) and get prices/details.
*   **Cart Management**: Inspect, add, update, and remove items from your cart.
*   **Order History**: List recent orders and view details.
*   **Authentication**: Securely manage your session credentials.

## Installation & Usage

### Method 1: Installation-Free (Recommended via uvx)
You can run the server directly using `uvx` (part of the `uv` package manager). This requires no manual installation or cloning.

**MCP Client Configuration (e.g., Claude Desktop, Cursor):**

```json
{
  "mcpServers": {
    "mercadona": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/aganoob/mercadona-mcp", "mercadona-mcp"]
    }
  }
}
```

By default, the server looks for credentials in `~/.mercadona_auth.json`. You can override this by adding an environment variable:

```json
      "env": {
        "MERCADONA_AUTH_FILE": "/path/to/custom/auth_config.json"
      }
```

### Method 2: Manual Installation via pip
1.  **Clone and Install**:
    ```bash
    git clone https://github.com/aganoob/mercadona-mcp
    cd mercadona-mcp
    pip install .
    ```
2.  **Run**:
    ```bash
    mercadona-mcp
    ```

## Authentication

This server requires a valid Mercadona session token.

1.  Log in to [tienda.mercadona.es](https://tienda.mercadona.es).
2.  Open Developer Tools (F12) -> **Application** -> **Local Storage**.
3.  Copy the value of the key `MO-user`.
4.  Open Developer Tools (F12) -> **Application** -> **Cookies**.
5.  Find the `__mo_da` cookie and decode/copy its value (contains `warehouse` and `postalCode`).
6.  Create the file `~/.mercadona_auth.json` (or your custom path) with the following structure:
    ```json
    {
      "local_storage": {
        "MO-user": "PASTE_MO_USER_VALUE_HERE"
      },
      "location": {
          "postal_code": "46001",
          "warehouse_id": "4115"
      },
      "cookies": {}
    }
    ```

### Option B: AI-Assisted Login (Orchestrated)
If your AI assistant has access to a **Browser Tool** (like `puppeteer-mcp` or `browser-mcp`), it can perform the login for you:
1.  Ask the AI: *"Log me in to Mercadona."*
2.  The AI will use `get_login_instructions` and then its Browser Tool to open the login page.
3.  After you log in, the AI will grab the token (`MO-user`) and location (`__mo_da` cookie) and save them using `set_credentials` and `set_location`.

## Available Tools

| Tool | Description |
|------|-------------|
| `search_products` | Search for products by name (e.g., "leche", "pan"). |
| `get_product_details` | Get detailed info (nutrition, packaging) for a product ID. |
| `get_cart` | View current cart items and total. |
| `add_to_cart` | Add an item to the cart. |
| `remove_from_cart` | Remove an item from the cart. |
| `list_recent_orders` | View your past orders. |
| `set_credentials` | Save session token (`MO-user`) to config. |
| `set_location` | Save `postal_code` and `warehouse_id` to config. |
| `get_login_instructions` | Guides an AI on how to perform the login flow. |

## Resources
*   `mercadona://cart`: Real-time JSON view of your shopping cart.
