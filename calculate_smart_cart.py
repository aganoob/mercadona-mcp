import json
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

def parse_date(date_str):
    # Format mostly: '2026-01-15T18:00:00Z'
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None

def calculate_smart_cart():
    # 1. Load Data
    try:
        with open("orders_dump.json", "r") as f:
            orders = json.load(f)
    except FileNotFoundError:
        print("orders_dump.json not found. Please run fetch_orders.py first.")
        return

    print(f"Loaded {len(orders)} orders.")

    # 2. Filter & Sort
    # Sort by start_date descending (newest first)
    orders.sort(key=lambda x: x["start_date"], reverse=True)
    
    # Cutoff for analysis: 1 year
    cutoff_date = datetime.now().astimezone() - timedelta(days=365)
    
    valid_orders = []
    for o in orders:
        d = parse_date(o["start_date"])
        if d and d > cutoff_date:
            valid_orders.append(o)
            
    print(f"Analyzing {len(valid_orders)} orders from the last year.")
    
    # 3. Product Analysis
    product_stats = {} # pid -> {name, dates=[], qtys=[], latest_price}
    
    for order in valid_orders:
        order_date = parse_date(order["start_date"])
        # Use 'lines' if available (fetched via fetch_details)
        if "lines" not in order:
            continue
            
        for line in order["lines"]:
            # Handle executed lines vs product lines structure
            # In dump: 'product_id', 'product': {...}
            pid = line.get("product_id")
            if not pid: continue
            
            product = line.get("product", {})
            pname = product.get("display_name", "Unknown Product")
            qty = line.get("ordered_quantity", 0) # Use ordered or prepared? Ordered is intent.
            
            if pid not in product_stats:
                product_stats[pid] = {
                    "id": pid,
                    "name": pname,
                    "dates": [],
                    "qtys": [],
                    "last_price": line.get("unit_price") or product.get("price_instructions", {}).get("unit_price")
                }
                
            product_stats[pid]["dates"].append(order_date)
            product_stats[pid]["qtys"].append(qty)

    # 4. Compute Metrics
    recommendations = []
    discovery_candidates = []
    
    now = datetime.now().astimezone()
    
    for pid, stats in product_stats.items():
        dates = sorted(stats["dates"]) # Oldest to newest
        if not dates: continue
        
        last_purchased = dates[-1]
        days_since_last = (now - last_purchased).days
        
        # Frequency
        count = len(dates)
        total_qty = sum(stats["qtys"])
        avg_qty = total_qty / count if count > 0 else 1
        
        # Intervals
        intervals = []
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i-1]).days
            intervals.append(delta)
            
        if not intervals:
            avg_interval = 30 # Default if only purchased once? Or ignore?
            # If purchased once long ago -> probably don't need regularly
            # If purchased once recently -> maybe just started
        else:
            avg_interval = statistics.mean(intervals)
            
        stats["metrics"] = {
            "days_since_last": days_since_last,
            "avg_interval": avg_interval,
            "frequency": count,
            "avg_qty": avg_qty
        }
        
        # 5. Logic
        
        # RULE 1: Core Essentials (High Freq, Time to Buy)
        # If bought at least 3 times
        # And days_since_last >= avg_interval * 0.8 (Buffer)
        is_candidate = False
        reason = ""
        
        if count >= 3:
            # Check stock logic
            # Heuristic: If bought VERY recently (e.g. < 5 days or < 20% of interval), probably still have it.
            # Unless it's super high freq (daily bread).
            
            threshold = max(avg_interval * 0.6, 4) # At least 4 days gap usually
            if days_since_last >= threshold:
                is_candidate = True
                reason = "Regular replenishment"
        
        # RULE 2: "Discovery" / Rediscovery
        # High historical frequency (>= 5) but haven't bought in 2x interval
        # Maybe I forgot it existed.
        elif count >= 5 and days_since_last > (avg_interval * 2.5):
            # Add to discovery list, not main cart potentially?
            # Or add with low confidence.
            discovery_candidates.append({
                "id": pid,
                "name": stats["name"],
                "reason": f"Haven't bought in {days_since_last} days (Avg: {avg_interval:.1f})",
                "suggested_qty": 1
            })
            continue

        if is_candidate:
            suggested_qty = round(avg_qty)
            if suggested_qty < 1: suggested_qty = 1
            
            recommendations.append({
                "id": pid,
                "name": stats["name"],
                "reason": f"{reason} (Last: {days_since_last}d ago, Avg Int: {avg_interval:.1f}d)",
                "suggested_qty": int(suggested_qty),
                "frequency": count
            })

    # Sort recommendations by frequency (popularity)
    recommendations.sort(key=lambda x: x["frequency"], reverse=True)
    
    # Output
    output = {
        "generated_at": now.isoformat(),
        "items": recommendations,
        "discovery": discovery_candidates
    }
    
    with open("smart_cart_calculation.json", "w") as f:
        json.dump(output, f, indent=2)
        
    # Print Summary
    print("-" * 50)
    print("SMART CART RECOMMENDATIONS")
    print("-" * 50)
    for i, item in enumerate(recommendations):
        print(f"[{item['suggested_qty']}x] {item['name']} ({item['reason']})")
        
    print("-" * 50)
    print("DISCOVERY / FORGOTTEN ITEMS")
    print("-" * 50)
    for item in discovery_candidates:
        print(f"[?] {item['name']} - {item['reason']}")

if __name__ == "__main__":
    calculate_smart_cart()
