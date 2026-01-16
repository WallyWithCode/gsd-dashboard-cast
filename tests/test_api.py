import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from src.api.main import app


@pytest.fixture
def client():
    """Create TestClient for FastAPI app."""
    return TestClient(app)


def test_health_endpoint(client):
    """Health check returns status."""
    with patch("src.cast.discovery.get_cast_device", return_value=AsyncMock()):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "active_streams" in data
        assert "cast_device" in data


def test_health_endpoint_no_device(client):
    """Health check returns degraded when no Cast device."""
    with patch("src.cast.discovery.get_cast_device", return_value=None):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["cast_device"] == "unavailable"


def test_status_idle(client):
    """Status returns idle when no active stream."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"
    assert data["stream"] is None


def test_start_webhook(client):
    """Start webhook accepts request and returns session_id."""
    with patch("src.api.state.StreamManager"):
        response = client.post("/start", json={
            "url": "https://example.com",
            "quality": "1080p",
            "duration": 300
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "session_id" in data


def test_start_webhook_defaults(client):
    """Start webhook uses defaults for optional fields."""
    with patch("src.api.state.StreamManager"):
        response = client.post("/start", json={
            "url": "https://example.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "session_id" in data


def test_stop_webhook(client):
    """Stop webhook accepts request."""
    response = client.post("/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_start_invalid_url(client):
    """Start webhook rejects invalid URL."""
    response = client.post("/start", json={
        "url": "not-a-url",
        "quality": "1080p"
    })
    assert response.status_code == 422  # Pydantic validation error
