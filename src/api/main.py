"""
FastAPI application with lifespan management for Dashboard Cast Service.

Uses lifespan context manager for startup/shutdown logic and resource cleanup.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

from src.api.logging_config import configure_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup: Configure logging, initialize state
    Shutdown: Cleanup resources
    """
    # Startup: Configure logging, initialize state
    configure_logging()
    logger.info("app_startup", phase="webhook-api")

    # Future: Initialize StreamTracker here (Plan 02)

    yield

    # Shutdown: Cleanup
    logger.info("app_shutdown")
    # Future: Cleanup active streams (Plan 02)


app = FastAPI(
    title="Dashboard Cast Service",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint for basic health check."""
    return {"service": "Dashboard Cast Service", "status": "running"}
