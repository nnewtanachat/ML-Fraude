from sqlalchemy import Column, Integer, Float, Boolean, DateTime, func, Index
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

class RawTransaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_transactions_is_fraud", "is_fraud"),
        Index("idx_transactions_device_type", "device_type"),
        {"comment": "Raw fraud detection data from Kaggle"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_amount = Column(Float, nullable=True)
    hour_of_day = Column(Float, nullable=True)
    is_weekend = Column(Boolean, nullable=True)
    num_items = Column(Integer, nullable=True)
    customer_age = Column(Float, nullable=True)
    prev_transactions = Column(Float, nullable=True)
    distance_from_home = Column(Float, nullable=True)
    device_type = Column(Integer, nullable=True)
    network_quality = Column(Float, nullable=True)
    is_first_transaction = Column(Boolean, nullable=True)
    store_type = Column(Integer, nullable=True)
    velocity_score = Column(Float, nullable=True)
    is_fraud = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<RawTransaction(id={self.id}, amount={self.transaction_amount}, fraud={self.is_fraud})>"
