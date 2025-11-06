"""
Pytest configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    settings.debug = True
    settings.database_url = "sqlite:///:memory:"
    return settings


@pytest.fixture(scope="function")
def client():
    """
    Create a test client for FastAPI.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def sample_conversation():
    """Sample conversation data for testing."""
    return {
        "user_id": 1,
        "turns": [
            {"role": "user", "content": "Hello Eva!"},
            {"role": "assistant", "content": "Hey! How are you doing?"},
            {"role": "user", "content": "I'm good, thanks!"},
        ]
    }
