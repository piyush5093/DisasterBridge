"""
FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Based Disaster Response Management System for Resource "
    "Allocation and Relief Coordination — backend API.",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Permissive CORS for local dev with the Next.js frontend.
# Tighten `allow_origins` before deploying (Week 7-8 hardening).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root() -> dict:
    return {
        "message": f"{settings.APP_NAME} API is running",
        "docs": "/docs",
    }
