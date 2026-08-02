"""
DisasterZone Database Model
Represents a geographic disaster-affected zone with severity classification
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class DisasterType(str, enum.Enum):
    FLOOD      = "flood"
    EARTHQUAKE = "earthquake"
    CYCLONE    = "cyclone"
    LANDSLIDE  = "landslide"
    DROUGHT    = "drought"
    OTHER      = "other"


class DisasterZone(Base):
    __tablename__ = "disaster_zones"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    state           = Column(String(100), nullable=False)
    district        = Column(String(100), nullable=True)

    # Geospatial (lat/lon for now; PostGIS geometry in production)
    latitude        = Column(Float, nullable=False)
    longitude       = Column(Float, nullable=False)
    area_sq_km      = Column(Float, default=0.0)

    # Disaster info
    disaster_type   = Column(String(50), default=DisasterType.FLOOD)
    severity        = Column(String(20), default=SeverityLevel.MEDIUM)
    severity_score  = Column(Float, default=0.0)       # 0–10 scale

    # Population data
    population_affected = Column(Integer, default=0)
    population_total    = Column(Integer, default=0)

    # Vulnerability index (0–1): elderly + children + medically dependent
    vulnerability_index = Column(Float, default=0.0)

    # Source feed info
    source          = Column(String(100), default="manual")  # gdacs / usgs / ndma
    source_event_id = Column(String(200), nullable=True)
    description     = Column(Text, nullable=True)

    # Status
    is_active       = Column(Integer, default=1)   # 1=active, 0=resolved

    # Timestamps
    event_start     = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DisasterZone id={self.id} name={self.name} severity={self.severity}>"
