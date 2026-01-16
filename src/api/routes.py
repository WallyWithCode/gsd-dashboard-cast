"""
Webhook endpoint handlers for Dashboard Cast Service.

Implements /start and /stop endpoints following non-blocking pattern.
"""
from fastapi import BackgroundTasks
import uuid
import structlog

from src.api.models import StartRequest, StartResponse, StopResponse

logger = structlog.get_logger()


def register_routes(app):
    """Register all webhook routes."""

    @app.post("/start", response_model=StartResponse)
    async def start_cast(request: StartRequest, background_tasks: BackgroundTasks):
        """Start casting with auto-stop of previous stream.

        Endpoint returns immediately while stream runs in background.
        If a stream is already active, it will be stopped before starting new one.

        Args:
            request: StartRequest with url, quality, duration
            background_tasks: FastAPI background tasks for non-blocking execution

        Returns:
            StartResponse with status and session_id
        """
        logger.info("webhook_start", url=str(request.url), quality=request.quality, duration=request.duration)

        # Auto-stop previous stream (seamless transition)
        if app.state.stream_tracker.has_active_stream():
            await app.state.stream_tracker.stop_current_stream()

        # Start new stream in background
        session_id = str(uuid.uuid4())
        background_tasks.add_task(
            app.state.stream_tracker.start_stream,
            session_id,
            str(request.url),
            request.quality,
            request.duration
        )

        return StartResponse(status="success", session_id=session_id)

    @app.post("/stop", response_model=StopResponse)
    async def stop_cast():
        """Stop active casting session.

        Returns:
            StopResponse with status and message
        """
        logger.info("webhook_stop")

        if not app.state.stream_tracker.has_active_stream():
            return StopResponse(status="success", message="No active stream")

        await app.state.stream_tracker.stop_current_stream()
        return StopResponse(status="success", message="Stream stopped")
