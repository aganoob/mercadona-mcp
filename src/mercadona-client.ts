import axios, { AxiosInstance } from 'axios';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import { AuthConfig, Cart, Product, Order } from './types.js';

export class MercadonaClient {
    private static ALGOLIA_APP_ID = "7UZJKL1DJ0";
    private static ALGOLIA_API_KEY = "9d8f2e39e90df472b4f2e559a116fe17";
    private static BASE_URL = "https://tienda.mercadona.es/api";

    private authFile: string;
    private token: string | null = null;
    private uuid: string | null = null;
    private warehouseId: string = "4115"; // Default Valencia
    private postalCode: string | null = null;

    public get isLoggedIn(): boolean {
        return !!this.token && !!this.uuid;
    }

    public get currentPostalCode(): string | null {
        return this.postalCode;
    }

    public get currentWarehouseId(): string {
        return this.warehouseId;
    }

    constructor(authFile?: string) {
        this.authFile = authFile || process.env.MERCADONA_AUTH_FILE || path.join(os.homedir(), '.mercadona_auth.json');
        this.loadAuth();
    }

    private get algoliaUrl(): string {
        return `https://7UZJKL1DJ0-dsn.algolia.net/1/indexes/products_prod_${this.warehouseId}_es/query`;
    }

    private get commonParams(): string {
        return `?lang=es&wh=${this.warehouseId}`;
    }

    private loadAuth() {
        if (!fs.existsSync(this.authFile)) {
            console.warn(`Auth file ${this.authFile} not found. Using defaults.`);
            return;
        }

        try {
            const authConfig: AuthConfig = fs.readJsonSync(this.authFile);

            // Load MO-user
            if (authConfig.local_storage && authConfig.local_storage['MO-user']) {
                let moUser: any = authConfig.local_storage['MO-user'];
                if (typeof moUser === 'string') {
                    try {
                        moUser = JSON.parse(moUser);
                    } catch (e) {
                        console.error("Error decoding MO-user string", e);
                        moUser = {};
                    }
                }
                this.token = moUser.token;
                this.uuid = moUser.uuid;
            }

            // Load Location
            if (authConfig.location) {
                this.postalCode = authConfig.location.postal_code;
                this.warehouseId = authConfig.location.warehouse_id || "4115";
            } else if (authConfig.cookies && authConfig.cookies.__mo_da) {
                try {
                    const moDaVal = authConfig.cookies.__mo_da;
                    if (moDaVal.includes('{')) {
                        const moDa = JSON.parse(moDaVal);
                        this.warehouseId = moDa.warehouse || this.warehouseId;
                        this.postalCode = moDa.postalCode || this.postalCode;
                    }
                } catch (e) {
                    console.error(`Failed to parse __mo_da cookie: ${e}`);
                }
            }

        } catch (e) {
            console.warn(`Warning: Failed to load auth from ${this.authFile}: ${e}`);
        }
    }

    public saveAuth(moUserData?: any, locationData?: { postal_code: string; warehouse_id: string }): boolean {
        try {
            let currentConfig: AuthConfig = {};
            if (fs.existsSync(this.authFile)) {
                try {
                    currentConfig = fs.readJsonSync(this.authFile);
                } catch { }
            }

            if (moUserData) {
                if (!currentConfig.local_storage) currentConfig.local_storage = {};
                currentConfig.local_storage['MO-user'] = JSON.stringify(moUserData);
                this.token = moUserData.token;
                this.uuid = moUserData.uuid;
            }

            if (locationData) {
                currentConfig.location = {
                    postal_code: locationData.postal_code,
                    warehouse_id: locationData.warehouse_id
                };
                this.postalCode = locationData.postal_code;
                this.warehouseId = locationData.warehouse_id;
            }

            fs.writeJsonSync(this.authFile, currentConfig, { spaces: 2 });
            return true;
        } catch (e) {
            console.error(`Failed to save auth: ${e}`);
            return false;
        }
    }

    private get headers(): Record<string, string> {
        if (!this.token) this.loadAuth();
        return {
            "Authorization": `Bearer ${this.token}`,
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        };
    }

    public async searchProducts(query: string): Promise<Product[]> {
        const headers = {
            "x-algolia-application-id": MercadonaClient.ALGOLIA_APP_ID,
            "x-algolia-api-key": MercadonaClient.ALGOLIA_API_KEY,
            "Content-Type": "application/json"
        };
        const payload = { query };

        try {
            const response = await axios.post(this.algoliaUrl, payload, { headers, timeout: 10000 });
            if (response.status === 200) {
                const hits = response.data.hits || [];
                // Filter unavailable
                return hits.filter((h: Product) => h.published && !h.unavailable_from);
            }
            return [];
        } catch (e) {
            console.error(`Search exception: ${e}`);
            return [];
        }
    }

    public async getProductDetails(productId: string): Promise<Product | null> {
        const url = `${MercadonaClient.BASE_URL}/products/${productId}/`;
        try {
            const response = await axios.get(url, { headers: this.headers });
            if (response.status === 200) return response.data;
            return null;
        } catch (e) {
            console.error(`Get product details error: ${e}`);
            return null;
        }
    }

    public async getCart(): Promise<Cart | null> {
        if (!this.uuid) return null;
        const url = `${MercadonaClient.BASE_URL}/customers/${this.uuid}/cart/${this.commonParams}`;
        try {
            const response = await axios.get(url, { headers: this.headers });
            if (response.status === 200) return response.data;
            return null;
        } catch (e) {
            console.error(`Get cart error: ${e}`);
            return null;
        }
    }

    public async updateCartItems(items: Array<{ product_id: string; quantity: number }>): Promise<boolean> {
        const currentCart = await this.getCart();
        if (!currentCart) return false;

        const url = `${MercadonaClient.BASE_URL}/customers/${this.uuid}/cart/${this.commonParams}`;
        const payload = {
            id: currentCart.id,
            version: currentCart.version,
            lines: items
        };

        try {
            const response = await axios.put(url, payload, { headers: this.headers });
            return [200, 201].includes(response.status);
        } catch (e) {
            console.error(`Update cart error: ${e}`);
            return false;
        }
    }

    public async addToCart(productId: string, quantity: number = 1): Promise<boolean> {
        return this.addToCartBulk([{ product_id: productId, quantity }]);
    }

    public async addToCartBulk(items: Array<{ product_id: string; quantity: number }>): Promise<boolean> {
        const currentCart = await this.getCart();
        if (!currentCart) return false;

        const linesMap = new Map<string, { product_id: string; quantity: number }>();

        // Initialize with existing
        for (const line of currentCart.lines) {
            const pid = line.product.id;
            linesMap.set(pid, { product_id: pid, quantity: line.quantity });
        }

        // Add/Update new items
        for (const item of items) {
            if (!item.product_id) continue;

            if (linesMap.has(item.product_id)) {
                linesMap.get(item.product_id)!.quantity += (item.quantity || 1);
            } else {
                linesMap.set(item.product_id, {
                    product_id: item.product_id,
                    quantity: item.quantity || 1
                });
            }
        }

        return this.updateCartItems(Array.from(linesMap.values()));
    }

    public async removeFromCart(productId: string): Promise<boolean> {
        const currentCart = await this.getCart();
        if (!currentCart) return false;

        const lines = currentCart.lines
            .filter(line => line.product.id !== productId)
            .map(line => ({ product_id: line.product.id, quantity: line.quantity }));

        return this.updateCartItems(lines);
    }

    public async clearCart(): Promise<boolean> {
        return this.updateCartItems([]);
    }

    public async listOrders(limit: number = 5): Promise<Order[]> {
        if (!this.uuid) return [];
        const url = `${MercadonaClient.BASE_URL}/customers/${this.uuid}/orders/`;
        try {
            const response = await axios.get(url, { headers: this.headers });
            if (response.status === 200) {
                return (response.data.results || []).slice(0, limit);
            }
            return [];
        } catch (e) {
            console.error(`List orders error: ${e}`);
            return [];
        }
    }

    public async getOrderDetails(orderId: string): Promise<any[]> {
        if (!this.uuid) return [];
        const url = `${MercadonaClient.BASE_URL}/customers/${this.uuid}/orders/${orderId}/lines/prepared/`;
        try {
            const response = await axios.get(url, { headers: this.headers });
            if (response.status === 200) {
                return response.data.results || [];
            }
            return [];
        } catch (e) {
            // Silent fail or log debug
            return [];
        }
    }
}
