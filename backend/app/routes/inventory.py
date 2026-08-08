from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import Inventory
from app.schemas.inventory import Inventory as InventorySchema, InventoryCreate

router = APIRouter()


@router.get("/", response_model=list[InventorySchema])
def list_inventory(db: Session = Depends(get_db)):
    return db.query(Inventory).all()


@router.post("/", response_model=InventorySchema)
def create_inventory(item: InventoryCreate, db: Session = Depends(get_db)):
    db_item = Inventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
