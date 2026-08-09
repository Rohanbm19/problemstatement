from fastapi import FastAPI
from src.preprocessing import load_data
from src.forecast import forecast_demand
from src.stockout import calculate_stockout


app = FastAPI(
    title="TwinStock AI ML Service",
    description="Demand forecasting and stockout prediction service",
    version="1.0.0"
)


DATA_PATH = "data/warehouse_cleaned.csv"


@app.get("/")
def root():
    return {
        "message": "TwinStock AI ML Service is running"
    }


@app.get("/forecast")
def get_forecast(days: int = 7):

    df = load_data(DATA_PATH)

    result = forecast_demand(df, days)

    return result.to_dict(orient="records")


@app.get("/stockout-risk")
def get_stockout_risk():

    df = load_data(DATA_PATH)

    result = calculate_stockout(df)

    return result.to_dict(orient="records")