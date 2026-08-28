import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load variables from .env
load_dotenv()

# Get database URL or default to local SQLite DB
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# Fix Heroku/Render/Railway 'postgres://' URI scheme
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Helper function to create engine with fallback
def init_engine(url):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    
    try:
        eng = create_engine(url, pool_pre_ping=True)
        # Verify connection
        with eng.connect() as conn:
            pass
        return eng
    except Exception as err:
        print(f"[Warning] Failed to connect to primary DB ({url}): {err}")
        print("[Fallback] Falling back to SQLite database at sqlite:///./app.db")
        return create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False}, pool_pre_ping=True)

# Create engine
engine = init_engine(DATABASE_URL)

# Create database session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for our database models
Base = declarative_base()


# Database dependency for FastAPI
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()