export interface Product {
    id: string;
    limit: number;
    packaging: string;
    published: boolean;
    share_url: string;
    thumbnail: string;
    display_name: string;
    unavailable_from: null | string;
    price_instructions: {
        iva: number;
        is_new: boolean;
        is_pack: boolean;
        pack_size: number;
        unit_name: string;
        unit_size: number;
        bulk_price: string;
        unit_price: string;
        approx_size: boolean;
        size_format: string;
        total_units: number;
        unit_selector: boolean;
        bunch_selector: boolean;
        drained_weight: number;
        selling_method: number;
        price_decreased: boolean;
        reference_price: string;
        min_bunch_amount: number;
        reference_format: string;
        increment_bunch_amount: number;
    };
}

export interface CartLine {
    id: string;
    type: string;
    product: Product;
    quantity: number;
}

export interface Cart {
    id: string;
    lines: CartLine[];
    version: number;
    summary: {
        total: number;
    };
}

export interface Order {
    id: string;
    start_date: string;
    end_date: string;
    status: string;
    total: number;
    // Add other fields as necessary
}

export interface AuthConfig {
    local_storage?: {
        "MO-user"?: string | { token: string; uuid: string };
    };
    location?: {
        postal_code: string;
        warehouse_id: string;
    };
    cookies?: {
        __mo_da?: string;
    };
}
