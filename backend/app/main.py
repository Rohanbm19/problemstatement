import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine, Base, SessionLocal
from app.models.inventory import InventoryItem
from app.models.transaction import Transaction

# Routes
from app.routes.inventory import router as inventory_router
from app.routes.transactions import router as transaction_router
from app.routes.forecast import router as forecast_router
from app.routes.products import router as products_router
from app.routes.sales import router as sales_router
from app.routes.suppliers import router as suppliers_router
from app.import_csv import import_inventory


# ============================================================
# STARTUP SEEDING & LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as err:
        print(f"[TwinStock AI Warning] Table creation failed on engine: {err}")
        from sqlalchemy import create_engine as ce
        sqlite_engine = ce("sqlite:///./app.db", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=sqlite_engine)

    # Auto-seed initial inventory data if table is empty
    db = SessionLocal()
    try:
        count = db.query(InventoryItem).count()
        if count == 0:
            print("[TwinStock AI] Database empty. Auto-seeding inventory data...")
            import_inventory()
    except Exception as err:
        print(f"[TwinStock AI] Auto-seed notice: {err}")
    finally:
        db.close()
        
    yield


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="TwinStock AI API",
    description="AI-powered warehouse inventory and replenishment backend",
    version="1.0.0",
    lifespan=lifespan
)

# Configurable CORS
raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in raw_origins.split(",")] if raw_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INCLUDE ROUTES
# ============================================================

app.include_router(inventory_router)
app.include_router(transaction_router)
app.include_router(forecast_router)
app.include_router(products_router, prefix="/products", tags=["Products"])
app.include_router(sales_router, prefix="/sales", tags=["Sales"])
app.include_router(suppliers_router, prefix="/suppliers", tags=["Suppliers"])


# ============================================================
# ROOT & HEALTH
# ============================================================

@app.get("/")
def root():
    return {
        "service": "TwinStock AI Backend API",
        "status": "running",
        "docs": "/docs"
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