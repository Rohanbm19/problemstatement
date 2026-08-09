import pandas as pd


def calculate_stockout(df: pd.DataFrame):

    df = df.copy()

    df["days_until_stockout"] = (
        df["stock_level"] /
        df["daily_demand"].replace(0, 0.01)
    )

    df["stockout_risk"] = "LOW"

    df.loc[
        df["days_until_stockout"] <= df["lead_time_days"],
        "stockout_risk"
    ] = "HIGH"

    df.loc[
        (df["days_until_stockout"] > df["lead_time_days"]) &
        (df["days_until_stockout"] <= df["lead_time_days"] + 3),
        "stockout_risk"
    ] = "MEDIUM"

    return df[
        [
            "item_id",
            "days_until_stockout",
            "lead_time_days",
            "stockout_risk"
        ]
    ]