from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime

from app.database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)

    item_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    category = Column(
        String(100),
        nullable=False
    )

    stock_level = Column(
        Integer,
        nullable=False
    )

    reorder_point = Column(
        Integer,
        nullable=False
    )

    reorder_frequency_days = Column(
        Integer,
        nullable=False
    )

    lead_time_days = Column(
        Integer,
        nullable=False
    )

    daily_demand = Column(
        Float,
        nullable=False
    )

    demand_std_dev = Column(
        Float,
        nullable=False
    )

    item_popularity_score = Column(
        Float,
        nullable=False
    )

    storage_location_id = Column(
        String(50),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )