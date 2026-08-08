from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sales import Sale
from app.schemas.product import Product as ProductSchema

router = APIRouter()


@router.get("/", response_model=list[ProductSchema])
def list_sales(db: Session = Depends(get_db)):
    return db.query(Sale).all()


@router.post("/", response_model=ProductSchema)
def create_sale(sale: dict, db: Session = Depends(get_db)):
    db_sale = Sale(**sale)
    db.add(db_sale)
    db.commit()
    db.refresh(db_sale)
    return db_sale
