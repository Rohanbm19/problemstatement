from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine, Base

# Models
from app.models.inventory import InventoryItem
from app.models.transaction import Transaction

# Routes
from app.routes.inventory import router as inventory_router
from app.routes.transactions import router as transaction_router


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="TwinStock AI API",
    description="AI-powered warehouse inventory and replenishment backend",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# DATABASE TABLE CREATION
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# ROUTES
# ============================================================

app.include_router(inventory_router)

app.include_router(transaction_router)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "TwinStock AI Backend is running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():

    try:

        with engine.connect() as connection:

            connection.execute(
                text("SELECT 1")
            )


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