from src.data_cleaning import clean_warehouse_data
from src.preprocessing import prepare_features
from src.forecast import forecast_demand
from src.stockout import detect_stockout_risk
from src.recommendation import build_recommendations


def run_pipeline(raw_data_path: str, cleaned_data_path: str):
    cleaned_df = clean_warehouse_data(raw_data_path)
    cleaned_df.to_csv(cleaned_data_path, index=False)

    features = prepare_features(cleaned_df)
    forecast = forecast_demand(features)
    stockout_risk = detect_stockout_risk(features)
    recommendations = build_recommendations(stockout_risk, forecast)

    return {
        "forecast": forecast,
        "stockout_risk": stockout_risk,
        "recommendations": recommendations,
    }


if __name__ == "__main__":
    result = run_pipeline("data/warehouse_raw.csv", "data/warehouse_cleaned.csv")
    print(result)
