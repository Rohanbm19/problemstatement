from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import timedelta
import httpx

from app.database import get_db
from app.models.inventory import InventoryItem
from app.models.transaction import Transaction


router = APIRouter(
    prefix="/forecast",
    tags=["Forecasting"]
)

ML_SERVICE_URL = "http://127.0.0.1:8001"


@router.post("/{item_id}")
async def generate_forecast(
    item_id: str,
    horizon: int = 7,
    db: Session = Depends(get_db)
):

    # ========================================================
    # VALIDATION
    # ========================================================

    item_id = item_id.strip()

    if not item_id:
        raise HTTPException(
            status_code=400,
            detail="Item ID is required"
        )

    if horizon <= 0:
        raise HTTPException(
            status_code=400,
            detail="Forecast horizon must be greater than 0"
        )

    if horizon > 30:
        raise HTTPException(
            status_code=400,
            detail="Forecast horizon cannot be greater than 30 days"
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
            detail=f"Product {item_id} not found"
        )

    # ========================================================
    # GET TRANSACTIONS
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
            )
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

        # ---------------------------------------------
        # Only dispatch represents customer demand
        # ---------------------------------------------

        if transaction_type != "dispatch":
            continue

        # ---------------------------------------------
        # Transaction must have a date
        # ---------------------------------------------

        if transaction.created_at is None:
            print(
                f"WARNING: Transaction {transaction.id} "
                f"has no created_at value"
            )
            continue

        transaction_date = (
            transaction.created_at.date()
        )

        # ---------------------------------------------
        # Add demand for that day
        # ---------------------------------------------

        if transaction_date not in daily_demand:

            daily_demand[transaction_date] = 0

        daily_demand[transaction_date] += (
            transaction.quantity
        )

    # ========================================================
    # CHECK DEMAND
    # ========================================================

    if not daily_demand:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Transactions were found for {item_id}, "
                "but no valid dispatch demand dates "
                "were available. "
                "Check the created_at column in the "
                "transactions table."
            )
        )

    # ========================================================
    # CREATE CONTINUOUS HISTORY
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

        history.append({
            "date": current_date.isoformat(),
            "demand": daily_demand.get(
                current_date,
                0
            )
        })

        current_date += timedelta(days=1)

    # ========================================================
    # NEED AT LEAST 2 DAYS
    # ========================================================

    if len(history) < 2:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Only one day of demand exists for "
                f"{item_id}. "
                "Create dispatch transactions on "
                "multiple dates before forecasting."
            )
        )

    # ========================================================
    # DEBUG
    # ========================================================

    print("\n====================================")
    print("FORECAST REQUEST")
    print("====================================")
    print("Item:", item_id)
    print("Current Stock:", item.stock_level)
    print("Transactions:", len(transactions))
    print("Demand History:", history)
    print("Horizon:", horizon)
    print("====================================\n")

    # ========================================================
    # CALL ML SERVICE
    # ========================================================

    try:

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(

                f"{ML_SERVICE_URL}/forecast",

                json={
                    "item_id": item_id,
                    "horizon": horizon,
                    "history": history
                }
            )

    except httpx.ConnectError:

        raise HTTPException(
            status_code=503,
            detail=(
                "ML service is not running. "
                "Start it on http://127.0.0.1:8001"
            )
        )

    except httpx.TimeoutException:

        raise HTTPException(
            status_code=504,
            detail="ML forecasting service timed out."
        )

    except httpx.RequestError as e:

        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to ML service: {str(e)}"
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
                "ML forecasting service failed"
            )
        )

    # ========================================================
    # ML RESULT
    # ========================================================

    result = response.json()

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "success": True,

        "item_id": item_id,

        "current_stock": item.stock_level,

        "history_days": len(history),

        "history": history,

        "model": result.get(
            "model",
            "Unknown"
        ),

        "horizon": result.get(
            "horizon",
            horizon
        ),

        "forecast": result.get(
            "forecast",
            []
        )
    }