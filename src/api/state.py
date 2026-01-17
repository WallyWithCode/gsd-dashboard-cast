"""
StreamTracker for managing active streaming tasks.

Manages asyncio tasks for long-running streams with proper lifecycle and cleanup.
"""
import asyncio
import structlog
from typing import Dict, Optional
from src.video.stream import StreamManager

logger = structlog.get_logger()


class StreamTracker:
    """Manages active streaming tasks with proper lifecycle and cleanup."""

    def __init__(self):
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()

    def has_active_stream(self) -> bool:
        """Check if there are any active streaming tasks."""
        return len(self.active_tasks) > 0

    async def start_stream(self, session_id: str, url: str, quality: str, duration: Optional[int], mode: str = 'hls') -> str:
        """Launch stream as background task.

        Args:
            session_id: Unique identifier for this stream session
            url: Target URL to cast
            quality: Quality preset ('1080p', '720p', 'low-latency')
            duration: Optional duration in seconds (None = indefinite)
            mode: Streaming mode ('hls' or 'fmp4')

        Returns:
            session_id for tracking
        """
        task = asyncio.create_task(self._run_stream(session_id, url, quality, duration, mode))
        self.active_tasks[session_id] = task
        logger.info("stream_task_created", session_id=session_id, url=url, quality=quality)
        return session_id

    async def _run_stream(self, session_id: str, url: str, quality: str, duration: Optional[int], mode: str = 'hls'):
        """Execute stream (runs until duration expires or cancelled).

        This is the background task that actually runs the stream. It binds
        context variables for logging and ensures cleanup in finally block.
        """
        try:
            structlog.contextvars.bind_contextvars(
                session_id=session_id,
                url=url,
                quality=quality,
                mode=mode
            )

            # TODO: Get cast_device_name from environment variable (Plan 03)
            # For now, hardcoding as placeholder
            cast_device_name = "Living Room TV"

            stream_manager = StreamManager(
                url=url,
                cast_device_name=cast_device_name,
                quality_preset=quality,
                duration=duration,
                mode=mode
            )
            await stream_manager.start_stream()

            logger.info("stream_completed", session_id=session_id)
        except asyncio.CancelledError:
            logger.info("stream_cancelled", session_id=session_id)
        except Exception as e:
            logger.error("stream_failed", session_id=session_id, error=str(e))
        finally:
            self.active_tasks.pop(session_id, None)
            structlog.contextvars.clear_contextvars()

    async def stop_current_stream(self):
        """Stop the active stream (single device, only one active)."""
        async with self.lock:
            if not self.active_tasks:
                return

            session_id, task = next(iter(self.active_tasks.items()))
            logger.info("stopping_stream", session_id=session_id)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def cleanup_all(self):
        """Cancel all active streams on shutdown."""
        tasks = list(self.active_tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.active_tasks.clear()
