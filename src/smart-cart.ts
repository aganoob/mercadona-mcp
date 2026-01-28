import { MercadonaClient } from './mercadona-client.js';
import fs from 'fs-extra';
import path from 'path';
import os from 'os';
// Removed unused date-fns import

// Minimal statistics implementation
function mean(numbers: number[]): number {
    if (numbers.length === 0) return 0;
    return numbers.reduce((a, b) => a + b, 0) / numbers.length;
}

export async function calculateSmartCart(client: MercadonaClient): Promise<string> {
    const orders = await client.listOrders(100);
    if (!orders || orders.length === 0) {
        return "No order history found.";
    }

    const cutoffDate = new Date();
    cutoffDate.setFullYear(cutoffDate.getFullYear() - 1);

    const productStats: Record<string, {
        id: string;
        name: string;
        dates: Date[];
        qtys: number[];
    }> = {};

    for (const order of orders) {
        if (!order.start_date) continue;
        const orderDate = new Date(order.start_date);

        if (orderDate < cutoffDate) continue;

        const orderLines = await client.getOrderDetails(order.id);
        if (!orderLines) continue;

        for (const line of orderLines) {
            const pid = line.product_id;
            if (!pid) continue;

            const product = line.product || {};
            const pname = product.display_name || "Unknown Product";
            const qty = line.ordered_quantity || 0;

            if (!productStats[pid]) {
                productStats[pid] = { id: pid, name: pname, dates: [], qtys: [] };
            }
            productStats[pid].dates.push(orderDate);
            productStats[pid].qtys.push(qty);
        }
    }

    const recommendations = [];
    const now = new Date();

    for (const pid in productStats) {
        const stats = productStats[pid];
        const dates = stats.dates.sort((a, b) => a.getTime() - b.getTime());

        if (dates.length === 0) continue;

        const lastPurchased = dates[dates.length - 1];
        const daysSinceLast = Math.floor((now.getTime() - lastPurchased.getTime()) / (1000 * 60 * 60 * 24));
        const count = dates.length;
        const totalQty = stats.qtys.reduce((a, b) => a + b, 0);
        const avgQty = count > 0 ? totalQty / count : 1;

        const intervals = [];
        for (let i = 1; i < dates.length; i++) {
            const delta = Math.floor((dates[i].getTime() - dates[i - 1].getTime()) / (1000 * 60 * 60 * 24));
            intervals.push(delta);
        }

        const avgInterval = intervals.length > 0 ? mean(intervals) : 30;

        // Logic: bought 3+ times
        if (count >= 3) {
            const threshold = Math.max(avgInterval * 0.6, 4);
            if (daysSinceLast >= threshold) {
                let suggestedQty = Math.round(avgQty);
                if (suggestedQty < 1) suggestedQty = 1;

                recommendations.push({
                    id: pid,
                    name: stats.name,
                    reason: `Regular replenishment (Last: ${daysSinceLast}d ago, Avg Int: ${avgInterval.toFixed(1)}d)`,
                    suggested_qty: suggestedQty,
                    frequency: count
                });
            }
        }
    }

    recommendations.sort((a, b) => b.frequency - a.frequency);

    const output = {
        generated_at: now.toISOString(),
        items: recommendations,
        discovery: []
    };

    const outputPath = path.join(os.homedir(), 'smart_cart_calculation.json');
    await fs.writeJson(outputPath, output, { spaces: 2 });

    return `Smart cart calculated with ${recommendations.length} recommendations. Saved to ${outputPath}.\n\n` +
        "INSTRUCTION TO ORCHESTRATOR: Please read the contents of this file and present it as a pretty markdown table " +
        "with columns: ID, Name, Suggested Qty.";
}
