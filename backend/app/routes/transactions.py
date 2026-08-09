from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import InventoryItem
from app.models.transaction import Transaction


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


class TransactionCreate(BaseModel):
    item_id: str
    transaction_type: str
    quantity: int
    location: str | None = None
    notes: str | None = None


@router.post("/")
def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db)
):

    # ------------------------------------------------
    # Validate quantity
    # ------------------------------------------------

    if data.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    # ------------------------------------------------
    # Find inventory item
    # ------------------------------------------------

    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.item_id == data.item_id
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # ------------------------------------------------
    # Normalize transaction type
    # ------------------------------------------------

    transaction_type = data.transaction_type.lower().strip()

    # ------------------------------------------------
    # Update inventory stock
    # ------------------------------------------------

    if transaction_type in ["receive", "return"]:

        item.stock_level += data.quantity

    elif transaction_type in ["dispatch", "damaged"]:

        if item.stock_level < data.quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient stock"
            )

        item.stock_level -= data.quantity

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid transaction type. "
                "Use receive, dispatch, return or damaged."
            )
        )

    # ------------------------------------------------
    # Create transaction record
    # ------------------------------------------------

    transaction = Transaction(
        item_id=data.item_id,
        transaction_type=transaction_type,
        quantity=data.quantity,
        location=data.location,
        notes=data.notes
    )

    db.add(transaction)

    # ------------------------------------------------
    # Save changes
    # ------------------------------------------------

    db.commit()

    db.refresh(item)
    db.refresh(transaction)

    # ------------------------------------------------
    # Return result
    # ------------------------------------------------

    return {
        "message": "Transaction successful",

        "transaction": {
            "id": transaction.id,
            "item_id": transaction.item_id,
            "type": transaction.transaction_type,
            "quantity": transaction.quantity,
            "location": transaction.location,
            "notes": transaction.notes,
            "created_at": transaction.created_at
        },

        "inventory": {
            "item_id": item.item_id,
            "stock_level": item.stock_level
        }
    }