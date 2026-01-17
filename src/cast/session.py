"""Cast session lifecycle management.

Provides a context manager for managing Cast sessions with automatic
HDMI-CEC wake and proper resource cleanup.
"""

from typing import Optional
import asyncio
import logging
import pychromecast
from .retry import retry_with_backoff
from .discovery import get_device_name

logger = logging.getLogger(__name__)


class CastSessionManager:
    """Manages Cast session lifecycle with automatic cleanup and HDMI-CEC wake.

    Provides async context manager pattern for Cast sessions with:
    - Automatic HDMI-CEC wake signal to turn on TV
    - Exponential backoff retry for connection reliability
    - Proper resource cleanup on exit
    - Graceful error handling

    The context manager ensures the TV is awake and ready before returning,
    and automatically stops any active media and disconnects on exit.

    Usage:
        device = await get_cast_device("Living Room TV")
        async with CastSessionManager(device) as session:
            session.start_cast("http://example.com/video.mp4")
            # Session automatically cleaned up on exit

    Attributes:
        device: The pychromecast Chromecast device
        is_active: Boolean indicating if session is currently active
    """

    def __init__(self, device: pychromecast.Chromecast):
        """Initialize session manager with Cast device.

        Args:
            device: Chromecast device from discovery
        """
        self.device = device
        self.is_active = False

    async def __aenter__(self):
        """Enter context manager - start Cast session with HDMI-CEC wake and retry logic.

        Establishes connection to the Cast device with automatic retry on failure,
        then sends HDMI-CEC wake signal to turn on the TV. Includes a 2-second
        delay after wake to allow TV to fully initialize.

        Returns:
            Self for context manager pattern

        Raises:
            Exception: If connection fails after all retry attempts
        """
        logger.info(f"Starting Cast session for device: {get_device_name(self.device)}")

        try:
            loop = asyncio.get_event_loop()

            # Wait for device to be ready with retry (blocking call)
            async def wait_for_device():
                await loop.run_in_executor(None, self.device.wait)
                logger.debug("Device ready")

            await retry_with_backoff(
                wait_for_device,
                max_retries=3,
                initial_delay=1.0,
                exceptions=(ConnectionError, TimeoutError, Exception)
            )

            # Wake TV via HDMI-CEC by unmuting volume
            # This triggers HDMI-CEC wake signal built into pychromecast
            await loop.run_in_executor(
                None,
                lambda: self.device.set_volume_muted(False)
            )
            logger.info("HDMI-CEC wake signal sent (unmute)")

            # Give TV time to wake up and establish connection
            await asyncio.sleep(2)

            self.is_active = True
            logger.info("Cast session active")
            return self

        except Exception as e:
            logger.error(f"Failed to start Cast session: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - clean up Cast session."""
        logger.info("Stopping Cast session...")

        try:
            # Stop any active media
            if self.is_active:
                await self.stop_cast()

            # Disconnect from device
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.device.disconnect)
            logger.debug("Device disconnected")

            self.is_active = False
            logger.info("Cast session cleanup complete")

        except Exception as e:
            logger.warning(f"Error during Cast session cleanup: {e}")

        # Don't suppress exceptions
        return False

    def start_cast(self, media_url: str):
        """Start casting media to device.

        Initiates media playback on the Cast device. Currently a placeholder
        that verifies the session is active and logs the request. Full video
        streaming implementation will be added in Phase 3.

        Args:
            media_url: URL of media to cast

        Raises:
            RuntimeError: If session not initialized (must use context manager)

        Note:
            Phase 3 implementation will:
            - Load media controller
            - Queue media URL
            - Start playback
            - Monitor playback status
        """
        if not self.is_active:
            logger.error("Cannot start cast - session not active")
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")

        logger.info(f"Cast request received for: {media_url}")
        logger.debug("Actual streaming implementation will be added in Phase 3")

        # Phase 3 will implement:
        # - Load media controller
        # - Queue media URL
        # - Start playback
        # - Monitor playback status

    async def stop_cast(self):
        """Stop active media playback and disconnect cast session.

        Stops any currently playing media on the Cast device. Safe to call
        even if no media is playing.

        Note:
            This is called automatically by __aexit__ during cleanup.
        """
        if not self.is_active:
            logger.debug("No active cast to stop")
            return

        logger.info("Stopping active cast...")

        try:
            # Stop media playback
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.device.media_controller.stop()
            )
            logger.debug("Media playback stopped")

        except Exception as e:
            logger.warning(f"Error stopping media playback: {e}")

        self.is_active = False
        logger.info("Cast stopped")
