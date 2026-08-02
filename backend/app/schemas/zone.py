"""
Pydantic Schemas for DisasterZone API (request/response validation)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.zone import SeverityLevel, DisasterType


# ── CREATE ──────────────────────────────────────────────────────────────────
class ZoneCreate(BaseModel):
    name: str                   = Field(..., example="Kerala — Wayanad")
    state: str                  = Field(..., example="Kerala")
    district: Optional[str]     = Field(None, example="Wayanad")
    latitude: float             = Field(..., example=11.6854)
    longitude: float            = Field(..., example=76.1320)
    area_sq_km: float           = Field(0.0)
    disaster_type: str          = Field(DisasterType.FLOOD, example="flood")
    severity: str               = Field(SeverityLevel.MEDIUM, example="critical")
    severity_score: float       = Field(0.0, ge=0.0, le=10.0, example=9.4)
    population_affected: int    = Field(0, example=18200)
    population_total: int       = Field(0, example=500000)
    vulnerability_index: float  = Field(0.0, ge=0.0, le=1.0, example=0.72)
    source: str                 = Field("manual", example="gdacs")
    source_event_id: Optional[str] = None
    description: Optional[str]  = None


# ── UPDATE (partial) ─────────────────────────────────────────────────────────
class ZoneUpdate(BaseModel):
    severity: Optional[str]             = None
    severity_score: Optional[float]     = None
    population_affected: Optional[int]  = None
    vulnerability_index: Optional[float]= None
    is_active: Optional[int]            = None
    description: Optional[str]          = None


# ── RESPONSE ─────────────────────────────────────────────────────────────────
class ZoneResponse(BaseModel):
    id: int
    name: str
    state: str
    district: Optional[str]
    latitude: float
    longitude: float
    area_sq_km: float
    disaster_type: str
    severity: str
    severity_score: float
    population_affected: int
    population_total: int
    vulnerability_index: float
    source: str
    source_event_id: Optional[str]
    description: Optional[str]
    is_active: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
