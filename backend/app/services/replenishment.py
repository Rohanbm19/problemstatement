def calculate_replenishment(item):
    stock = float(item.stock_level)
    daily_demand = float(item.daily_demand)
    lead_time = float(item.lead_time_days)
    demand_std = float(item.demand_std_dev)

    # No demand
    if daily_demand <= 0:
        return {
            "safety_stock": 0,
            "lead_time_demand": 0,
            "recommended_order_quantity": 0,
            "reason": "No current demand detected"
        }

    # Expected demand during supplier lead time
    lead_time_demand = daily_demand * lead_time

    # Simple safety stock calculation
    safety_stock = 1.65 * demand_std * (lead_time ** 0.5)

    # Target inventory
    target_stock = lead_time_demand + safety_stock

    # Recommended order quantity
    recommended_order = max(
        0,
        target_stock - stock
    )

    return {
        "safety_stock": round(safety_stock, 2),
        "lead_time_demand": round(lead_time_demand, 2),
        "target_stock": round(target_stock, 2),
        "recommended_order_quantity": round(
            recommended_order
        ),
        "reason": (
            "Order quantity is based on expected "
            "lead-time demand, safety stock, and "
            "current inventory."
        )
    }