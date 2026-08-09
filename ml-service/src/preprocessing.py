import pandas as pd


def load_data(path: str):
    df = pd.read_csv(path)

    required_columns = [
        "item_id",
        "stock_level",
        "reorder_point",
        "lead_time_days",
        "daily_demand",
        "demand_std_dev",
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = df.dropna(subset=required_columns)

    return df