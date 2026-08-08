from pydantic import BaseModel


class InventoryBase(BaseModel):
    product_id: int
    quantity: int


class InventoryCreate(InventoryBase):
    pass


class Inventory(InventoryBase):
    id: int

    class Config:
        orm_mode = True
