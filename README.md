# Mercadona MCP Server

![Claude Desktop](https://img.shields.io/badge/Claude%20Desktop-Compatible-f54e00?style=flat&logo=anthropic)
![Cursor](https://img.shields.io/badge/Cursor-Compatible-000000?style=flat&logo=cursor)
![Antigravity](https://img.shields.io/badge/Antigravity-Compatible-8a2be2?style=flat)

An **MCP Server** for the [Mercadona Online Store](https://tienda.mercadona.es).
This server gives AI assistants (like Claude or Cursor) superpowers to manage your grocery shopping: search products, build carts, and analyze your history.

---

## 🚀 Quick Start

Add this to your `claude_desktop_config.json` or Cursor MCP settings. No manual installation required!

```json
{
  "mcpServers": {
    "mercadona": {
      "command": "npx",
      "args": ["-y", "mercadona-mcp"] 
    }
  }
}
```

> **First Run:** You need to log in. Just ask your AI: **"Log me in to Mercadona"** and follow the instructions it gives you (it uses the `login` tool).

---

## ✨ Capabilities

### 🛒 Product Search & Details
*   **Search**: find products by name (e.g., "leche", "hummus"). The server filters out unavailable items.
*   **Details**: Get full specs, packaging info, and nutrition facts.

### 📦 Complete Cart Management
*   **View Cart**: See what's currently in your basket and the total price.
*   **Add/Remove**: Add single items or **bulk add** multiple items at once.
*   **Clear**: Empty the entire cart in one go.

### 🧠 Smart Cart (AI-Powered)
*   **Predictive Shopping**: The `calculate_smart_cart` tool analyzes your last year of orders to find items you buy regularly (e.g., every 2 weeks) and checks if you are due for a restock.
*   **Resource**: View the results anytime at `mercadona://smart_cart`.

### 📜 Order History
*   **Recent Orders**: List your last purchases.
*   **Resource**: Get a fast JSON dump at `mercadona://recent_orders`.

### ⚡ Live Resources
The server exposes **MCP Resources**:
| Resource | Description |
| :--- | :--- |
| `mercadona://cart` | Live JSON view of your current shopping cart. |
| `mercadona://smart_cart` | The latest recommendations from the Smart Cart algorithm. |
| `mercadona://recent_orders` | A list of your last 20 orders. |

---

## 🔐 Authentication

This server needs a valid Mercadona session (`MO-user` token) and location data (`postal_code`, `warehouse_id`) to work.

### Option A: AI-Assisted (Recommended)
1.  **Ask**: "Log me in to Mercadona."
2.  **Follow**: The AI will use the `login` tool to guide you. It usually involves:
    *   Opening a browser to the login page.
    *   You logging in manually.
    *   The AI grabbing the credentials from the browser storage and saving them strictly to your local machine (`~/.mercadona_auth.json`).

### Option B: Manual Setup
If you prefer to grab the token yourself:
1.  Log in to [tienda.mercadona.es](https://tienda.mercadona.es).
2.  Open **Developer Tools (F12)** > **Application**.
    *   **Local Storage**: Copy the value of `MO-user`.
    *   **Cookies**: Find `__mo_da` and decode it (it contains your warehouse/zip).
3.  Create `~/.mercadona_auth.json`:
    ```json
    {
        "local_storage": {
            "MO-user": "{\"token\": \"...\", \"uuid\": \"...\"}"
        },
        "location": {
            "postal_code": "46001",
            "warehouse_id": "4115"
        }
    }
    ```

---

## 🛠️ Configuration

You can override the default auth file location using an environment variable:

```json
"env": {
  "MERCADONA_AUTH_FILE": "/absolute/path/to/my_auth.json"
}
```

## 👩‍💻 Development

To run from source:

```bash
git clone https://github.com/aganoob/mercadona-mcp
cd mercadona-mcp
npm install
npm run build
npm start
```

### Legacy Python
The original Python implementation is available in `legacy_python/`.
