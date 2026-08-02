"""
Resource inventory CRUD endpoints, plus a geospatial "nearest depots"
query — the kind of lookup Week 3-4's demand-prediction/allocation
modules will need ("which depots are within reach of this affected zone").
"""

from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query

from app.models.disaster_event import GeoPoint
from app.models.resource_inventory import ResourceInventory, ResourceStatus, ResourceType
from app.schemas.resource_inventory import ResourceCreate, ResourceOut, ResourceUpdate

router = APIRouter(prefix="/resources", tags=["resources"])


def _to_out(doc: ResourceInventory) -> ResourceOut:
    return ResourceOut(
        id=str(doc.id),
        depot_name=doc.depot_name,
        resource_type=doc.resource_type,
        quantity=doc.quantity,
        unit=doc.unit,
        capacity=doc.capacity,
        longitude=doc.location.coordinates[0],
        latitude=doc.location.coordinates[1],
        address=doc.address,
        status=doc.status,
        contact_phone=doc.contact_phone,
        notes=doc.notes,
        last_restocked_at=doc.last_restocked_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("", response_model=ResourceOut, status_code=201)
async def create_resource(payload: ResourceCreate) -> ResourceOut:
    doc = ResourceInventory(
        depot_name=payload.depot_name,
        resource_type=payload.resource_type,
        quantity=payload.quantity,
        unit=payload.unit,
        capacity=payload.capacity,
        location=GeoPoint(coordinates=[payload.longitude, payload.latitude]),
        address=payload.address,
        status=payload.status,
        contact_phone=payload.contact_phone,
        notes=payload.notes,
    )
    await doc.insert()
    return _to_out(doc)


@router.get("", response_model=list[ResourceOut])
async def list_resources(
    resource_type: ResourceType | None = Query(None),
    status: ResourceStatus | None = Query(None),
    limit: int = Query(100, le=500),
) -> list[ResourceOut]:
    conditions = []
    if resource_type:
        conditions.append(ResourceInventory.resource_type == resource_type)
    if status:
        conditions.append(ResourceInventory.status == status)

    docs = await ResourceInventory.find(*conditions).limit(limit).to_list()
    return [_to_out(d) for d in docs]


@router.get("/near", response_model=list[ResourceOut])
async def find_nearby_resources(
    longitude: float = Query(...),
    latitude: float = Query(...),
    radius_km: float = Query(50, gt=0, le=1000),
    resource_type: ResourceType | None = Query(None),
) -> list[ResourceOut]:
    """Depots within `radius_km` of a point, nearest first (e.g. an affected zone's centroid)."""
    EARTH_RADIUS_KM = 6371.0
    query: dict = {
        "location": {
            "$geoWithin": {"$centerSphere": [[longitude, latitude], radius_km / EARTH_RADIUS_KM]}
        }
    }
    if resource_type:
        query["resource_type"] = resource_type.value

    docs = await ResourceInventory.find(query).to_list()
    return [_to_out(d) for d in docs]


@router.get("/{resource_id}", response_model=ResourceOut)
async def get_resource(resource_id: PydanticObjectId) -> ResourceOut:
    doc = await ResourceInventory.get(resource_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return _to_out(doc)


@router.put("/{resource_id}", response_model=ResourceOut)
async def update_resource(resource_id: PydanticObjectId, payload: ResourceUpdate) -> ResourceOut:
    doc = await ResourceInventory.get(resource_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    updates = payload.model_dump(exclude_unset=True)
    lon = updates.pop("longitude", None)
    lat = updates.pop("latitude", None)
    if lon is not None or lat is not None:
        current_lon, current_lat = doc.location.coordinates
        doc.location = GeoPoint(coordinates=[lon if lon is not None else current_lon, lat if lat is not None else current_lat])

    quantity_restocked = "quantity" in updates and updates["quantity"] > doc.quantity
    for key, value in updates.items():
        setattr(doc, key, value)
    if quantity_restocked:
        doc.last_restocked_at = datetime.now(timezone.utc)

    doc.updated_at = datetime.now(timezone.utc)
    await doc.save()
    return _to_out(doc)


@router.delete("/{resource_id}", status_code=204)
async def delete_resource(resource_id: PydanticObjectId) -> None:
    doc = await ResourceInventory.get(resource_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    await doc.delete()
