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


ML_SERVICE_URL = "http://127.0.0.1:8001"


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

    if not transactions:

        raise HTTPException(
            status_code=400,
            detail=(
                f"No transactions found for {item_id}. "
                "Create dispatch transactions first."
            ),
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

        # ----------------------------------------------------
        # Only dispatch is demand
        # ----------------------------------------------------

        if transaction_type != "dispatch":
            continue

        # ----------------------------------------------------
        # Require created_at
        # ----------------------------------------------------

        if transaction.created_at is None:

            print(
                f"WARNING: Transaction "
                f"{transaction.id} "
                f"has no created_at"
            )

            continue

        transaction_date = (
            transaction.created_at.date()
        )

        # ----------------------------------------------------
        # Aggregate demand by date
        # ----------------------------------------------------

        daily_demand.setdefault(
            transaction_date,
            0,
        )

        daily_demand[
            transaction_date
        ] += transaction.quantity

    # ========================================================
    # NO DISPATCH DEMAND
    # ========================================================

    if not daily_demand:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Transactions were found for {item_id}, "
                "but there are no dispatch transactions "
                "with valid dates."
            ),
        )

    # ========================================================
    # CREATE CONTINUOUS DAILY HISTORY
    # ========================================================

    first_date = min(
        daily_demand.keys()
    )

    last_date = max(
        daily_demand.keys()
    )

    history = []

    current_date = first_date

    while current_date <= last_date:

        history.append(
            {
                "date": current_date.isoformat(),
                "demand": daily_demand.get(
                    current_date,
                    0,
                ),
            }
        )

        current_date += timedelta(
            days=1
        )

    # ========================================================
    # DEMO MINIMUM
    #
    # Granite demo mode requires 7 real daily observations.
    # ========================================================

    if len(history) < 7:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {len(history)} days of "
                f"continuous demand history exist "
                f"for {item_id}. "
                "Create dispatch transactions "
                "across at least 7 different dates "
                "for the demo forecast."
            ),
        )

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