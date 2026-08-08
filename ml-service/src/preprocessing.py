import pandas as pd


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df["Lag_1"] = df["Demand"].shift(1)
    return df
