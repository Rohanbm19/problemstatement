from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import InventoryItem
from app.services.stockout import calculate_stockout_risk
from app.services.replenishment import calculate_replenishment


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


# Get all inventory
@router.get("/")
def get_inventory(
    db: Session = Depends(get_db)
):
    return db.query(InventoryItem).all()


# Get low-stock items
@router.get("/low-stock")
def get_low_stock(
    db: Session = Depends(get_db)
):
    return (
        db.query(InventoryItem)
        .filter(
            InventoryItem.stock_level
            <= InventoryItem.reorder_point
        )
        .all()
    )


# Get stockout risk for an item
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


# Get replenishment recommendation
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


# Get a single inventory item
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