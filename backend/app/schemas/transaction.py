from pydantic import BaseModel


class TransactionBase(BaseModel):
    product_id: int
    type: str
    quantity: int


class TransactionCreate(TransactionBase):
    pass


class Transaction(TransactionBase):
    id: int

    class Config:
        orm_mode = True
