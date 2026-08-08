import pandas as pd


def clean_warehouse_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df = df.dropna()
    df = df.rename(columns={"date": "Date", "sku": "SKU", "demand": "Demand"})
    df["Demand"] = df["Demand"].astype(float)
    return df
