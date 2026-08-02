"""
Aggregates all v1 routers into a single APIRouter that main.py mounts.

As new modules are built (resource inventory on Day 9, zones on Day 10,
demand prediction in Week 3, etc.) their routers get included here —
this file is the one place that grows, endpoint files stay independent.
"""

from fastapi import APIRouter

from app.api.v1 import (
    buildings,
    health,
    imagery,
    impact,
    ingestion,
    ingestion_ndma,
    ingestion_usgs,
    pipeline,
    population,
    resources,
    zones,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ingestion.router)
api_router.include_router(ingestion.events_router)
api_router.include_router(ingestion_usgs.router)
api_router.include_router(ingestion_ndma.router)
api_router.include_router(pipeline.router)
api_router.include_router(impact.router)
api_router.include_router(population.router)
api_router.include_router(buildings.router)
api_router.include_router(resources.router)
api_router.include_router(zones.router)
api_router.include_router(imagery.router)
