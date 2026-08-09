from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.inventory import InventoryItem
from app.services.stockout import calculate_stockout_risk
from app.services.replenishment import calculate_replenishment


# =========================================================
# INVENTORY ROUTER
# =========================================================

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


# =========================================================
# STOCK DISPATCH REQUEST MODEL
# =========================================================

class StockUpdate(BaseModel):
    quantity: int


# =========================================================
# GET ALL INVENTORY
# =========================================================

@router.get("/")
def get_inventory(
    db: Session = Depends(get_db)
):
    return db.query(InventoryItem).all()


# =========================================================
# GET LOW-STOCK ITEMS
# =========================================================

@router.get("/low-stock")
def get_low_stock(
    db: Session = Depends(get_db)
):
    return (
        db.query(InventoryItem)
        .filter(
            InventoryItem.stock_level <= InventoryItem.reorder_point
        )
        .all()
    )


# =========================================================
# GET STOCKOUT RISK
# =========================================================

@router.get("/{item_id}/stockout-risk")
def get_stockout_risk(
    item_id: str,
    db: Session = Depends(get_db)
):

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
            detail="Item not found"
        )

    risk = calculate_stockout_risk(item)

    return {
        "item_id": item.item_id,
        "stock_level": item.stock_level,
        "daily_demand": item.daily_demand,
        "lead_time_days": item.lead_time_days,
        **risk
    }


# =========================================================
# GET REPLENISHMENT RECOMMENDATION
# =========================================================

@router.get("/{item_id}/recommendation")
def get_replenishment_recommendation(
    item_id: str,
    db: Session = Depends(get_db)
):

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
            detail="Item not found"
        )

    recommendation = calculate_replenishment(item)

    return {
        "item_id": item.item_id,
        "category": item.category,
        "current_stock": item.stock_level,
        "daily_demand": item.daily_demand,
        "lead_time_days": item.lead_time_days,
        **recommendation
    }


# =========================================================
# GET SINGLE INVENTORY ITEM
# =========================================================

@router.get("/{item_id}")
def get_inventory_item(
    item_id: str,
    db: Session = Depends(get_db)
):

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
            detail="Item not found"
        )

    return item


# =========================================================
# PUT - DISPATCH / SUBTRACT STOCK
# =========================================================

@router.put("/{item_id}")
def update_inventory(
    item_id: str,
    data: StockUpdate,
    db: Session = Depends(get_db)
):

    # Find product
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
            detail="Product not found"
        )

    # Validate quantity
    if data.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    # Prevent stock from becoming negative
    if item.stock_level < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Current stock is {item.stock_level}"
        )

    # SUBTRACT quantity from current stock
    old_stock = item.stock_level

    item.stock_level = item.stock_level - data.quantity

    # Save changes
    db.commit()
    db.refresh(item)

    return {
        "message": "Inventory updated successfully",

        "item": {
            "item_id": item.item_id,
            "category": item.category,
            "old_stock_level": old_stock,
            "dispatched_quantity": data.quantity,
            "new_stock_level": item.stock_level,
            "reorder_point": item.reorder_point,
            "storage_location_id": item.storage_location_id
        }
    }