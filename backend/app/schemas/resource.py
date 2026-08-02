"""
Pydantic Schemas for Resource, Depot, and Team APIs
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ══════════════════════════════════════════════
#  RESOURCE SCHEMAS
# ══════════════════════════════════════════════

class ResourceCreate(BaseModel):
    name: str               = Field(..., example="Food Packets")
    category: str           = Field(..., example="food")
    unit: str               = Field("units", example="units")
    quantity_available: int = Field(0, example=42000)
    quantity_total: int     = Field(0, example=50000)
    quantity_deployed: int  = Field(0, example=8000)
    depot_id: Optional[int] = None
    critical_threshold: float = Field(0.20, example=0.20)

class ResourceUpdate(BaseModel):
    quantity_available: Optional[int]  = None
    quantity_deployed: Optional[int]   = None
    quantity_total: Optional[int]      = None

class ResourceResponse(BaseModel):
    id: int
    name: str
    category: str
    unit: str
    quantity_available: int
    quantity_total: int
    quantity_deployed: int
    depot_id: Optional[int]
    critical_threshold: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
#  DEPOT SCHEMAS
# ══════════════════════════════════════════════

class DepotCreate(BaseModel):
    name: str           = Field(..., example="Delhi HQ Depot")
    city: str           = Field(..., example="New Delhi")
    state: str          = Field(..., example="Delhi")
    latitude: float     = Field(..., example=28.6139)
    longitude: float    = Field(..., example=77.2090)
    capacity_units: int = Field(100000)
    contact_name: Optional[str]  = None
    contact_phone: Optional[str] = None

class DepotResponse(BaseModel):
    id: int
    name: str
    city: str
    state: str
    latitude: float
    longitude: float
    capacity_units: int
    is_active: int
    contact_name: Optional[str]
    contact_phone: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
#  FIELD TEAM SCHEMAS
# ══════════════════════════════════════════════

class TeamCreate(BaseModel):
    team_code: str      = Field(..., example="Alpha-7")
    team_name: str      = Field(..., example="Alpha Response Team 7")
    members: int        = Field(0, example=12)
    zone_id: Optional[int]  = None
    depot_id: Optional[int] = None
    status: str         = Field("standby", example="deployed")
    location_txt: Optional[str] = Field(None, example="Wayanad, Kerala")
    lead_name: Optional[str]    = None
    lead_phone: Optional[str]   = None

class TeamResponse(BaseModel):
    id: int
    team_code: str
    team_name: str
    members: int
    zone_id: Optional[int]
    depot_id: Optional[int]
    status: str
    current_lat: Optional[float]
    current_lon: Optional[float]
    location_txt: Optional[str]
    lead_name: Optional[str]
    lead_phone: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
