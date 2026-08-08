import pandas as pd


def detect_stockout_risk(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"risk": []}
    return {"risk": [{"sku": row["SKU"], "demand": row["Demand"]} for _, row in df.head(5).iterrows()]}
