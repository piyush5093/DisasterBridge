"""
Pydantic Schemas for DisasterEvent API
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EventResponse(BaseModel):
    id: int
    source: str
    event_id: Optional[str]
    title: Optional[str]
    disaster_type: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    country: Optional[str]
    region: Optional[str]
    magnitude: Optional[float]
    alert_level: Optional[str]
    fetched_at: datetime
    event_date: Optional[datetime]
    zone_id: Optional[int]

    class Config:
        from_attributes = True


class TeamStatusUpdate(BaseModel):
    status: str
    location_txt: Optional[str] = None
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None
