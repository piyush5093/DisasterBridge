from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from database import Base
import uuid
from datetime import datetime
import enum

# --- ENUMS ---
class SourceEnum(str, enum.Enum):
    gdacs = 'gdacs'
    usgs = 'usgs'
    ndma = 'ndma'

class EventTypeEnum(str, enum.Enum):
    flood = 'flood'
    earthquake = 'earthquake'
    cyclone = 'cyclone'
    drought = 'drought'
    wildfire = 'wildfire'
    other = 'other'

class AlertLevelEnum(str, enum.Enum):
    green = 'green'
    orange = 'orange'
    red = 'red'
    low = 'low'
    medium = 'medium'
    high = 'high'
    critical = 'critical'

class ResourceTypeEnum(str, enum.Enum):
    food = 'food'
    hygiene_kits = 'hygiene_kits'
    medical = 'medical'
    shelter = 'shelter'
    vehicle = 'vehicle'
    other = 'other'

class ResourceStatusEnum(str, enum.Enum):
    available = 'available'
    reserved = 'reserved'
    deployed = 'deployed'
    depleted = 'depleted'

class PriorityEnum(str, enum.Enum):
    low = 'low'
    medium = 'medium'
    high = 'high'

class RoadStatusEnum(str, enum.Enum):
    open = 'open'
    blocked = 'blocked'
    unknown = 'unknown'

class MissionStatusEnum(str, enum.Enum):
    pending = 'pending'
    assigned = 'assigned'
    in_transit = 'in_transit'
    delivered = 'delivered'
    cancelled = 'cancelled'

# --- MODELS ---

class DisasterEvent(Base):
    __tablename__ = 'disaster_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(SQLEnum(SourceEnum), nullable=False)
    event_type = Column(SQLEnum(EventTypeEnum), nullable=False)
    alert_level = Column(SQLEnum(AlertLevelEnum), nullable=False)
    magnitude = Column(Float, nullable=True)
    location = Column(Geometry('POINT', srid=4326), nullable=False)
    impact_extent = Column(Geometry('POLYGON', srid=4326), nullable=True)
    population_exposed = Column(Integer, nullable=True)
    buildings_affected = Column(Integer, nullable=True)
    critical_infrastructure_count = Column(Integer, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    event_time = Column(DateTime, nullable=True)

class ResourceItem(Base):
    __tablename__ = 'resource_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(SQLEnum(ResourceTypeEnum), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    location = Column(Geometry('POINT', srid=4326), nullable=False)
    depot_name = Column(String, nullable=False)
    status = Column(SQLEnum(ResourceStatusEnum), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GridCell(Base):
    __tablename__ = 'grid_cells'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cell_geometry = Column(Geometry('POLYGON', srid=4326), nullable=False)
    related_event_id = Column(UUID(as_uuid=True), ForeignKey('disaster_events.id'), nullable=False)
    severity_score = Column(Float, nullable=True) # 0-100
    population_exposed = Column(Integer, nullable=True)
    predicted_demand_food = Column(Float, nullable=True)
    predicted_demand_hygiene_kits = Column(Float, nullable=True)
    predicted_demand_medical = Column(Float, nullable=True)
    predicted_demand_shelter = Column(Float, nullable=True)
    priority = Column(SQLEnum(PriorityEnum), nullable=True)
    priority_override = Column(SQLEnum(PriorityEnum), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PredictionRecord(Base):
    __tablename__ = 'prediction_records'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('grid_cells.id'), nullable=False)
    predicted_food = Column(Float, nullable=False)
    predicted_hygiene_kits = Column(Float, nullable=False)
    predicted_medical = Column(Float, nullable=False)
    predicted_shelter = Column(Float, nullable=False)
    confidence_interval_low = Column(JSON, nullable=True)
    confidence_interval_high = Column(JSON, nullable=True)
    model_version = Column(String, nullable=False)
    is_latest = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    recalibration_reason = Column(String, nullable=True)

class AllocationPlan(Base):
    __tablename__ = 'allocation_plans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('grid_cells.id'), nullable=False)
    resource_type = Column(SQLEnum(ResourceTypeEnum), nullable=False)
    allocated_quantity = Column(Float, nullable=False)
    source_depot_id = Column(UUID(as_uuid=True), ForeignKey('resource_items.id'), nullable=False)
    coverage_percent = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    plan_run_id = Column(UUID(as_uuid=True), nullable=False)

class Route(Base):
    __tablename__ = 'routes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_run_id = Column(UUID(as_uuid=True), nullable=False)
    depot_id = Column(UUID(as_uuid=True), ForeignKey('resource_items.id'), nullable=False)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('grid_cells.id'), nullable=False)
    route_geometry = Column(Geometry('LINESTRING', srid=4326), nullable=True)
    distance_km = Column(Float, nullable=False)
    estimated_duration_minutes = Column(Float, nullable=False)
    is_fallback_straight_line = Column(Boolean, default=False)
    road_status = Column(SQLEnum(RoadStatusEnum), default=RoadStatusEnum.unknown)

class Mission(Base):
    __tablename__ = 'missions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('grid_cells.id'), nullable=False)
    team_name = Column(String, nullable=False)
    vehicle_id = Column(String, nullable=False)
    route_id = Column(UUID(as_uuid=True), ForeignKey('routes.id'), nullable=False)
    priority = Column(SQLEnum(PriorityEnum), nullable=False)
    status = Column(SQLEnum(MissionStatusEnum), default=MissionStatusEnum.pending)
    supplies = Column(JSON, nullable=False) # {food, water, medical_kits, shelter}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    dispatched_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    status_history = Column(JSON, nullable=True)


class Commander(Base):
    """
    Stores named commander accounts. Passwords are bcrypt-hashed.
    Each commander has a role ('commander' | 'admin') — currently
    all roles have the same data access; role is reserved for future RBAC.
    """
    __tablename__ = 'commanders'

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name     = Column(String(120), nullable=False)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(50), nullable=False, default='commander')
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
