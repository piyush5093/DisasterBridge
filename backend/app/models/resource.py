"""
Resource Inventory Database Model
Tracks all relief resources: food, water, medical, transport, shelter
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class ResourceCategory(str):
    FOOD      = "food"
    WATER     = "water"
    MEDICAL   = "medical"
    TRANSPORT = "transport"
    SHELTER   = "shelter"
    PERSONNEL = "personnel"


class Resource(Base):
    __tablename__ = "resources"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(200), nullable=False)        # e.g. "Food Packets"
    category     = Column(String(50),  nullable=False)        # food / water / medical / transport
    unit         = Column(String(50),  default="units")       # units / liters / kits / vehicles

    # Quantities
    quantity_available = Column(Integer, default=0)
    quantity_total     = Column(Integer, default=0)
    quantity_deployed  = Column(Integer, default=0)

    # Depot this resource belongs to (optional FK)
    depot_id     = Column(Integer, ForeignKey("depots.id"), nullable=True)

    # Thresholds
    critical_threshold = Column(Float, default=0.20)  # 20% → alert

    # Timestamps
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def availability_pct(self):
        if self.quantity_total == 0:
            return 0.0
        return round(self.quantity_available / self.quantity_total * 100, 1)

    def is_critical(self):
        return self.availability_pct() / 100 <= self.critical_threshold

    def __repr__(self):
        return f"<Resource id={self.id} name={self.name} available={self.quantity_available}>"
