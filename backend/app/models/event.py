"""
Field Team & Disaster Event Database Models
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base


class TeamStatus(str):
    DEPLOYED = "deployed"
    TRANSIT  = "transit"
    STANDBY  = "standby"
    OFFLINE  = "offline"


class FieldTeam(Base):
    __tablename__ = "field_teams"

    id           = Column(Integer, primary_key=True, index=True)
    team_code    = Column(String(20),  nullable=False, unique=True)  # e.g. "Alpha-7"
    team_name    = Column(String(200), nullable=False)
    members      = Column(Integer, default=0)

    # Assignment
    zone_id      = Column(Integer, ForeignKey("disaster_zones.id"), nullable=True)
    depot_id     = Column(Integer, ForeignKey("depots.id"),         nullable=True)
    status       = Column(String(30), default=TeamStatus.STANDBY)

    # Location
    current_lat  = Column(Float, nullable=True)
    current_lon  = Column(Float, nullable=True)
    location_txt = Column(String(200), nullable=True)   # "Wayanad, Kerala"

    # Contact
    lead_name    = Column(String(200), nullable=True)
    lead_phone   = Column(String(20),  nullable=True)

    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FieldTeam {self.team_code} status={self.status}>"


class DisasterEvent(Base):
    """Raw event log from external feeds (GDACS, USGS, NDMA)"""
    __tablename__ = "disaster_events"

    id           = Column(Integer, primary_key=True, index=True)
    source       = Column(String(50),  nullable=False)   # gdacs / usgs / ndma
    event_id     = Column(String(200), nullable=True)    # source's own ID
    title        = Column(String(500), nullable=True)
    disaster_type= Column(String(50),  nullable=True)

    latitude     = Column(Float, nullable=True)
    longitude    = Column(Float, nullable=True)
    country      = Column(String(100), nullable=True)
    region       = Column(String(200), nullable=True)

    magnitude    = Column(Float, nullable=True)         # earthquake magnitude / alert score
    alert_level  = Column(String(20), nullable=True)    # green / orange / red
    raw_data     = Column(Text, nullable=True)          # full JSON response stored

    fetched_at   = Column(DateTime, server_default=func.now())
    event_date   = Column(DateTime, nullable=True)

    # Link to classified zone (set after classifier runs)
    zone_id      = Column(Integer, ForeignKey("disaster_zones.id"), nullable=True)

    def __repr__(self):
        return f"<DisasterEvent id={self.id} source={self.source} type={self.disaster_type}>"
