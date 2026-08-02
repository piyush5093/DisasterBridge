"""
Resource inventory — depots/stockpiles of relief resources (food,
water, medical supplies, shelter kits, personnel, vehicles, etc.) that
Week 3-6's demand-prediction and allocation-optimization modules will
read from and write to (deducting allocated quantities, flagging
depleted depots).
"""

from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, GEOSPHERE, IndexModel

from app.models.disaster_event import GeoPoint


class ResourceType(str, Enum):
    FOOD = "food"
    WATER = "water"
    MEDICAL_SUPPLIES = "medical_supplies"
    SHELTER_KITS = "shelter_kits"
    BLANKETS = "blankets"
    GENERATORS = "generators"
    VEHICLES = "vehicles"
    PERSONNEL = "personnel"
    OTHER = "other"


class ResourceStatus(str, Enum):
    ACTIVE = "active"
    LOW_STOCK = "low_stock"
    DEPLETED = "depleted"
    IN_TRANSIT = "in_transit"
    DAMAGED = "damaged"


class ResourceInventory(Document):
    depot_name: str
    resource_type: ResourceType
    quantity: float
    unit: str  # "kg", "liters", "units", "personnel", "vehicles", ...
    capacity: float | None = None  # max storage capacity, same unit as `quantity`

    location: GeoPoint
    address: str | None = None

    status: ResourceStatus = ResourceStatus.ACTIVE
    contact_phone: str | None = None
    notes: str | None = None

    last_restocked_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "resource_inventory"
        indexes = [
            IndexModel([("location", GEOSPHERE)], name="geo_2dsphere"),
            IndexModel([("resource_type", ASCENDING)], name="idx_resource_type"),
            IndexModel([("status", ASCENDING)], name="idx_status"),
        ]
