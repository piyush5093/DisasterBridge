"""
Central application configuration.

Loads settings from environment variables / .env file using pydantic-settings.
All other modules should import `settings` from here instead of calling
os.environ directly, so configuration stays in one place.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Disaster Response Management System"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # --- Database (MongoDB) ---
    MONGODB_URL: str = "mongodb://disaster_admin:disaster_pass@localhost:27017/disaster_response?authSource=admin"
    MONGODB_DB_NAME: str = "disaster_response"

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # --- External data feeds (used starting Day 2) ---
    GDACS_API_BASE: str = "https://www.gdacs.org/gdacsapi/api"
    USGS_EARTHQUAKE_API_BASE: str = "https://earthquake.usgs.gov/fdsnws/event/1"
    NDMA_API_KEY: str = ""
    SENTINEL_HUB_CLIENT_ID: str = ""
    SENTINEL_HUB_CLIENT_SECRET: str = ""

    # --- Population density (Day 7) ---
    # Path to a local population-count GeoTIFF (e.g. downloaded from
    # WorldPop). See app/services/population/density_service.py's
    # docstring for how to obtain one — not fetched automatically.
    POPULATION_RASTER_PATH: str = "data/population/population_density.tif"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — avoids re-reading .env on every import."""
    return Settings()


settings = get_settings()
