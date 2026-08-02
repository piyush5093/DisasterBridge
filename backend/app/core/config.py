"""
App Configuration — reads from .env file
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App info
    APP_NAME: str = "AI Disaster Response Command System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./disaster_response.db"

    # External API Keys
    GDACS_API_URL: str = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    USGS_API_URL: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    NDMA_API_URL: str = "https://ndma.gov.in/api"  # placeholder

    GDACS_API_KEY: Optional[str] = None
    USGS_API_KEY: Optional[str] = None
    NDMA_API_KEY: Optional[str] = None

    # Severity thresholds
    CRITICAL_SCORE_MIN: float = 8.0
    HIGH_SCORE_MIN: float = 6.0
    MEDIUM_SCORE_MIN: float = 4.0

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
