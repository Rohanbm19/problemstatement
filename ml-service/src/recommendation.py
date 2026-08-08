def build_recommendations(stockout_risk: dict, forecast: dict) -> list[dict]:
    recommendations = []
    for item in stockout_risk.get("risk", []):
        recommendations.append({
            "sku": item.get("sku"),
            "action": "Reorder inventory",
            "forecast": forecast.get("forecast", []),
        })
    return recommendations
