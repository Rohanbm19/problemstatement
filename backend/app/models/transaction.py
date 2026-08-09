from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Transaction(Base):

    __tablename__ = "transactions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    item_id = Column(
        String(50),
        nullable=False,
        index=True
    )

    transaction_type = Column(
        String(20),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    location = Column(
        String(50),
        nullable=True
    )

    notes = Column(
        String(500),
        nullable=True
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )