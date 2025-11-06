"""
Test health check endpoint.
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the health check endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "character" in data


def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "character" in data
    assert data["character"] == "Eva"


def test_docs_available(client: TestClient):
    """Test that API docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
