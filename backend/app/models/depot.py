"""
Resource Depot Database Model
Physical warehouse/depot locations that hold and dispatch resources
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Depot(Base):
    __tablename__ = "depots"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)       # e.g. "Delhi HQ Depot"
    city        = Column(String(100), nullable=False)
    state       = Column(String(100), nullable=False)

    # Geospatial
    latitude    = Column(Float, nullable=False)
    longitude   = Column(Float, nullable=False)

    # Capacity
    capacity_units = Column(Integer, default=100000)
    is_active      = Column(Integer, default=1)

    # Contact
    contact_name   = Column(String(200), nullable=True)
    contact_phone  = Column(String(20),  nullable=True)

    # Relationship
    resources = relationship("Resource", backref="depot", lazy="dynamic")

    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Depot id={self.id} name={self.name} city={self.city}>"
