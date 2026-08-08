from fastapi import FastAPI

from app.database import Base, engine
from app.routes import inventory, products, sales, suppliers, transactions

app = FastAPI(title="Inventory Management Backend")

Base.metadata.create_all(bind=engine)

app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(sales.router, prefix="/sales", tags=["Sales"])
app.include_router(suppliers.router, prefix="/suppliers", tags=["Suppliers"])


@app.get("/")
def root():
    return {"message": "Backend is running"}
