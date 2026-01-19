"""
Webhook endpoint handlers for Dashboard Cast Service.

Implements /start and /stop endpoints following non-blocking pattern.
"""
import uuid
import structlog

from src.api.models import StartRequest, StartResponse, StopResponse, StatusResponse, HealthResponse
from src.cast.discovery import get_cast_device
from src.video.hardware import HardwareAcceleration

logger = structlog.get_logger()


def register_routes(app):
    """Register all webhook routes."""

    @app.post("/start", response_model=StartResponse)
    async def start_cast(request: StartRequest):
        """Start casting with auto-stop of previous stream.

        Endpoint returns immediately while stream runs in background.
        If a stream is already active, it will be stopped before starting new one.

        Args:
            request: StartRequest with url, quality, duration

        Returns:
            StartResponse with status and session_id
        """
        logger.info("webhook_start", url=str(request.url), quality=request.quality, duration=request.duration, mode=request.mode)

        # Auto-stop previous stream (seamless transition)
        if app.state.stream_tracker.has_active_stream():
            await app.state.stream_tracker.stop_current_stream()

        # Start new stream in background (create_task is non-blocking)
        session_id = str(uuid.uuid4())
        await app.state.stream_tracker.start_stream(
            session_id,
            str(request.url),
            request.quality,
            request.duration,
            request.mode
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

    @app.get("/status", response_model=StatusResponse)
    async def get_status():
        """Get current stream status.

        Returns idle or casting with stream info. Note that stream metadata
        (started_at, url, quality) is not tracked in StreamTracker v1.
        """
        if not app.state.stream_tracker.has_active_stream():
            return StatusResponse(status="idle", stream=None)

        # Return active stream info
        session_id, task = next(iter(app.state.stream_tracker.active_tasks.items()))

        # TODO: Track stream metadata (started_at, url, quality) in StreamTracker
        # For now, return basic info
        return StatusResponse(
            status="casting",
            stream={
                "session_id": session_id,
                "started_at": "TODO",  # Add timestamp tracking
                "url": "TODO",  # Add metadata tracking
                "quality": "TODO"
            }
        )

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check for monitoring.

        Checks Cast device availability, active streams, and hardware acceleration status.
        """
        # Check Cast device
        device = await get_cast_device()
        device_available = device is not None

        # Check hardware acceleration
        hw_accel = HardwareAcceleration()
        encoder_config = hw_accel.get_encoder_config()

        status = "healthy" if device_available else "degraded"

        return HealthResponse(
            status=status,
            active_streams=len(app.state.stream_tracker.active_tasks),
            cast_device="available" if device_available else "unavailable",
            hardware_acceleration={
                "quicksync_available": hw_accel.is_qsv_available(),
                "encoder": encoder_config['encoder']
            }
        )
