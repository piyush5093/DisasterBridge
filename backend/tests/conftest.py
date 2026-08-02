"""
conftest.py — Shared pytest fixtures for backend tests
"""
import os
import sys
import pytest

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
# Add project root (parent of backend) so optimizer/ package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db


# Use an in-memory SQLite DB for tests
TEST_DB_URL = "sqlite:///./test_disaster_response.db"

engine_test = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables before tests run, drop after."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    # Dispose all connections before cleanup (required on Windows)
    engine_test.dispose()
    try:
        if os.path.exists("test_disaster_response.db"):
            os.remove("test_disaster_response.db")
    except PermissionError:
        pass  # Windows: file still locked briefly, OK to skip


@pytest.fixture(scope="function")
def db_session():
    """Provide a clean DB session per test function."""
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="session")
def client():
    """FastAPI test client with DB dependency overridden."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
