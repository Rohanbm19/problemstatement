def calculate_stockout_risk(item):
    """
    Calculate basic stockout risk for an inventory item.
    """

    stock = float(item.stock_level)
    daily_demand = float(item.daily_demand)
    lead_time = float(item.lead_time_days)

    # Avoid division by zero
    if daily_demand <= 0:
        return {
            "days_until_stockout": None,
            "lead_time_demand": 0,
            "risk": "LOW"
        }

    # Estimated days until stock reaches zero
    days_until_stockout = stock / daily_demand

    # Expected demand during supplier lead time
    lead_time_demand = daily_demand * lead_time

    # Determine risk
    if days_until_stockout <= lead_time:
        risk = "HIGH"

    elif days_until_stockout <= lead_time + 3:
        risk = "MEDIUM"

    else:
        risk = "LOW"

    return {
        "days_until_stockout": round(days_until_stockout, 2),
        "lead_time_demand": round(lead_time_demand, 2),
        "risk": risk
    }