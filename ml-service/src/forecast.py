import pandas as pd


def forecast_demand(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"forecast": []}
    latest = df.iloc[-1]
    return {"forecast": [latest["Demand"]], "sku": latest.get("SKU", None)}
