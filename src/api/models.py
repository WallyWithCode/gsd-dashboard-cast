"""
Pydantic request/response models for webhook API endpoints.

All models use Pydantic v2 for validation and serialization.
"""
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional


class StartRequest(BaseModel):
    """Request model for starting a cast stream."""
    url: HttpUrl
    quality: str = "1080p"  # Default from Docker config
    duration: Optional[int] = None  # Seconds, None = indefinite


class StartResponse(BaseModel):
    """Response model for start endpoint."""
    status: str
    session_id: str


class StopResponse(BaseModel):
    """Response model for stop endpoint."""
    status: str
    message: str


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    status: str  # "casting" or "idle"
    stream: Optional[dict] = None  # {session_id, started_at, url, quality} if active


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str  # "healthy" or "degraded"
    active_streams: int
    cast_device: str  # "available" or "unavailable"
