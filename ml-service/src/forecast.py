import pandas as pd


def forecast_demand(df: pd.DataFrame, days: int = 7):

    df = df.copy()

    df["forecast_daily_demand"] = df["daily_demand"]

    df["forecast_demand"] = (
        df["forecast_daily_demand"] * days
    )

    return df[
        [
            "item_id",
            "forecast_daily_demand",
            "forecast_demand"
        ]
    ]