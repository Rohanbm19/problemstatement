from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import timedelta
import httpx

from app.database import get_db
from app.models.inventory import InventoryItem
from app.models.transaction import Transaction


router = APIRouter(
    prefix="/forecast",
    tags=["Forecasting"],
)


import os
from datetime import date, timedelta

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8001")


@router.post("/{item_id}")
async def generate_forecast(
    item_id: str,
    horizon: int = 7,
    db: Session = Depends(get_db),
):

    # ========================================================
    # VALIDATION
    # ========================================================

    item_id = item_id.strip()

    if not item_id:

        raise HTTPException(
            status_code=400,
            detail="Item ID is required",
        )

    if horizon <= 0:

        raise HTTPException(
            status_code=400,
            detail="Forecast horizon must be greater than 0",
        )

    if horizon > 30:

        raise HTTPException(
            status_code=400,
            detail="Forecast horizon cannot be greater than 30 days",
        )

    # ========================================================
    # CHECK PRODUCT
    # ========================================================

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == item_id
        )
        .first()
    )

    if not item:

        raise HTTPException(
            status_code=404,
            detail=f"Product {item_id} not found",
        )

    # ========================================================
    # GET TRANSACTIONS FROM DATABASE
    # ========================================================

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.item_id == item_id
        )
        .order_by(
            Transaction.created_at.asc()
        )
        .all()
    )

    # ========================================================
    # BUILD DAILY DEMAND
    # ========================================================

    daily_demand = {}

    for transaction in transactions:

        transaction_type = (
            transaction.transaction_type
            .lower()
            .strip()
        )

        if transaction_type != "dispatch":
            continue

        if transaction.created_at is None:
            continue

        transaction_date = transaction.created_at.date()
        daily_demand.setdefault(transaction_date, 0)
        daily_demand[transaction_date] += transaction.quantity

    # ========================================================
    # CREATE CONTINUOUS DAILY HISTORY (WITH FALLBACK)
    # ========================================================

    history = []

    if daily_demand:
        first_date = min(daily_demand.keys())
        last_date = max(daily_demand.keys())
        current_date = first_date
        while current_date <= last_date:
            history.append(
                {
                    "date": current_date.isoformat(),
                    "demand": daily_demand.get(current_date, 0),
                }
            )
            current_date += timedelta(days=1)

    # If transactions cover less than 7 days, extrapolate/fill using item.daily_demand
    if len(history) < 7:
        today = date.today()
        base_demand = float(item.daily_demand) if item.daily_demand and item.daily_demand > 0 else 10.0
        
        # Build 7-day history leading up to today
        history = []
        for i in range(7, 0, -1):
            d = today - timedelta(days=i)
            # Add slight variance if demand_std_dev exists
            variance = float(item.demand_std_dev or 1.0) * (0.1 if (i % 2 == 0) else -0.1)
            day_demand = max(1.0, round(base_demand + variance, 1))
            history.append({
                "date": d.isoformat(),
                "demand": day_demand
            })

    # ========================================================
    # DEBUG
    # ========================================================

    print("\n======================================")
    print("FORECAST REQUEST")
    print("======================================")
    print("Item:", item_id)
    print("Current Stock:", item.stock_level)
    print("Transactions:", len(transactions))
    print("History Days:", len(history))
    print("History:", history)
    print("Horizon:", horizon)
    print("======================================\n")

    # ========================================================
    # CALL ML SERVICE
    # ========================================================

    try:

        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:

            response = await client.post(
                f"{ML_SERVICE_URL}/forecast",
                json={
                    "item_id": item_id,
                    "horizon": horizon,
                    "history": history,
                },
            )

    except httpx.ConnectError:

        raise HTTPException(
            status_code=503,
            detail=(
                "ML service is not running. "
                "Start it on "
                "http://127.0.0.1:8001"
            ),
        )

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail=(
                "ML forecasting service timed out."
            ),
        )

    except httpx.RequestError as exc:

        raise HTTPException(
            status_code=503,
            detail=(
                "Could not connect to ML service: "
                f"{str(exc)}"
            ),
        )

    # ========================================================
    # ML ERROR
    # ========================================================

    if response.status_code != 200:

        try:

            error_data = response.json()

        except Exception:

            error_data = {}

        raise HTTPException(
            status_code=502,
            detail=error_data.get(
                "detail",
                "ML forecasting service failed",
            ),
        )

    # ========================================================
    # ML RESULT
    # ========================================================

    result = response.json()

    # ========================================================
    # RETURN TO FRONTEND
    # ========================================================

    return {
        "success": True,

        "item_id": item_id,

        "current_stock": item.stock_level,

        "history_days": len(history),

        "history": history,

        "model": result.get(
            "model",
            "Unknown",
        ),

        "horizon": result.get(
            "horizon",
            horizon,
        ),

        "forecast": result.get(
            "forecast",
            [],
        ),
    }