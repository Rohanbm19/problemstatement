from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    category: str | None = None
    price: float
    stock_quantity: int = 0


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int

    class Config:
        orm_mode = True
