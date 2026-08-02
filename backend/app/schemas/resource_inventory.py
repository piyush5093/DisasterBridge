from datetime import datetime

from pydantic import BaseModel, Field

from app.models.resource_inventory import ResourceStatus, ResourceType


class ResourceCreate(BaseModel):
    depot_name: str
    resource_type: ResourceType
    quantity: float = Field(ge=0)
    unit: str
    capacity: float | None = Field(default=None, ge=0)
    longitude: float
    latitude: float
    address: str | None = None
    status: ResourceStatus = ResourceStatus.ACTIVE
    contact_phone: str | None = None
    notes: str | None = None


class ResourceUpdate(BaseModel):
    """All fields optional — PATCH-style partial update."""

    depot_name: str | None = None
    resource_type: ResourceType | None = None
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None
    capacity: float | None = Field(default=None, ge=0)
    longitude: float | None = None
    latitude: float | None = None
    address: str | None = None
    status: ResourceStatus | None = None
    contact_phone: str | None = None
    notes: str | None = None


class ResourceOut(BaseModel):
    id: str
    depot_name: str
    resource_type: ResourceType
    quantity: float
    unit: str
    capacity: float | None
    longitude: float
    latitude: float
    address: str | None
    status: ResourceStatus
    contact_phone: str | None
    notes: str | None
    last_restocked_at: datetime | None
    created_at: datetime
    updated_at: datetime
