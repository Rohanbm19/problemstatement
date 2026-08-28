from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import InventoryItem

router = APIRouter()


@router.get("/")
def list_products(db: Session = Depends(get_db)):
    return db.query(InventoryItem).all()
