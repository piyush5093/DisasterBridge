"""
AI Disaster Response Management System
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import engine, Base
from app.api.routes import zones, resources, feeds, depots, teams, events, allocation, analytics
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create all tables
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created")
    print(f"[OK] AI Disaster Response API started -- {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    # Shutdown
    print("[STOP] API shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Based Disaster Response Management System for Resource Allocation and Relief Coordination",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(zones.router,      prefix="/api/zones",      tags=["Disaster Zones"])
app.include_router(resources.router,  prefix="/api/resources",  tags=["Resources"])
app.include_router(feeds.router,      prefix="/api/feeds",      tags=["Live Feeds"])
app.include_router(depots.router,     prefix="/api/depots",     tags=["Resource Depots"])
app.include_router(teams.router,      prefix="/api/teams",      tags=["Field Teams"])
app.include_router(events.router,     prefix="/api/events",     tags=["Disaster Events"])
app.include_router(allocation.router, prefix="/api/allocation", tags=["Resource Allocation"])
app.include_router(analytics.router,  prefix="/api/analytics",  tags=["Analytics"])


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "modules": {
            "data_ingestion":   "active",
            "zone_classifier":  "active",
            "demand_predictor": "active",
            "optimizer":        "active",
            "analytics":        "active",
        },
        "endpoints": {
            "zones":      "/api/zones",
            "resources":  "/api/resources",
            "feeds":      "/api/feeds",
            "depots":     "/api/depots",
            "teams":      "/api/teams",
            "events":     "/api/events",
            "allocation": "/api/allocation",
            "analytics":  "/api/analytics",
            "docs":       "/docs",
        }
    }
