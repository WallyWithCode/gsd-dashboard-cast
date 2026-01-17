"""
FastAPI application with lifespan management for Dashboard Cast Service.

Uses lifespan context manager for startup/shutdown logic and resource cleanup.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

from src.api.logging_config import configure_logging
from src.api.state import StreamTracker
from src.api.routes import register_routes
from src.video.server import StreamingServer

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup: Configure logging, initialize state, start streaming server
    Shutdown: Cleanup resources, stop streaming server
    """
    # Startup: Configure logging, initialize state
    configure_logging()
    logger.info("app_startup", phase="webhook-api")

    # Initialize StreamTracker
    app.state.stream_tracker = StreamTracker()

    # Start streaming server
    app.state.streaming_server = StreamingServer(port=8080)
    await app.state.streaming_server.start()
    logger.info("streaming_server_started", port=8080)

    yield

    # Shutdown: Cleanup active streams
    logger.info("app_shutdown", active_streams=len(app.state.stream_tracker.active_tasks))
    await app.state.stream_tracker.cleanup_all()
    await app.state.streaming_server.stop()
    logger.info("streaming_server_stopped")


app = FastAPI(
    title="Dashboard Cast Service",
    version="1.0.0",
    lifespan=lifespan
)

# Register webhook routes
register_routes(app)


@app.get("/")
async def root():
    """Root endpoint for basic health check."""
    return {"service": "Dashboard Cast Service", "status": "running"}
