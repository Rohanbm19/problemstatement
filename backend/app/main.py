from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine, Base
from app.models.inventory import InventoryItem
from app.routes.inventory import router as inventory_router


app = FastAPI(
    title="TwinStock AI API",
    description="AI-powered warehouse inventory and replenishment backend",
    version="1.0.0"
)


# Create database tables if they don't already exist
Base.metadata.create_all(bind=engine)


# Register inventory routes
app.include_router(inventory_router)


@app.get("/")
def root():
    return {
        "message": "TwinStock AI Backend is running"
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }