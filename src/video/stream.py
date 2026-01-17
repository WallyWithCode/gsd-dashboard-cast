"""Complete streaming orchestration from browser to Cast device.

Manages the lifecycle of all pipeline components:
1. Xvfb virtual display for headless rendering
2. Browser with authentication
3. FFmpeg video encoding
4. Cast session to Android TV

Supports automatic timeout/duration to stop streaming after configured time.
"""

import asyncio
import logging
from typing import Optional

from .capture import XvfbManager
from .encoder import FFmpegEncoder
from .quality import get_quality_config
from ..browser.manager import BrowserManager
from ..browser.auth import inject_auth
from ..cast.discovery import get_cast_device, get_device_name
from ..cast.session import CastSessionManager

logger = logging.getLogger(__name__)


class StreamManager:
    """Orchestrates complete streaming pipeline from browser to Cast.

    Manages the lifecycle of all components:
    1. Xvfb virtual display
    2. Browser with authentication
    3. FFmpeg video encoding
    4. Cast session to Android TV

    Supports automatic timeout/duration to stop streaming after configured time.

    Usage:
        manager = StreamManager(
            url="https://dashboard.local",
            cast_device_name="Living Room TV",
            quality_preset="1080p",
            duration=60  # Stop after 60 seconds
        )
        await manager.start_stream()
    """

    def __init__(
        self,
        url: str,
        cast_device_name: str,
        quality_preset: str = "720p",
        duration: Optional[int] = None,
        auth_config: Optional[dict] = None,
        mode: str = 'hls'
    ):
        """Initialize streaming manager.

        Args:
            url: Target URL to display and stream
            cast_device_name: Friendly name of Cast device
            quality_preset: Quality preset name ('1080p', '720p', 'low-latency')
            duration: Optional duration in seconds (None = stream indefinitely)
            auth_config: Optional authentication dict with cookies/localStorage
            mode: Streaming mode ('hls' or 'fmp4')

        Raises:
            ValueError: If quality_preset is not recognized
        """
        self.url = url
        self.cast_device_name = cast_device_name
        self.quality_preset = quality_preset
        self.duration = duration
        self.auth_config = auth_config
        self.mode = mode

        # Validate quality preset exists
        get_quality_config(quality_preset)  # Raises ValueError if invalid

        logger.info(
            f"StreamManager initialized: url={url}, device={cast_device_name}, "
            f"quality={quality_preset}, duration={duration}, mode={mode}"
        )

    async def start_stream(self) -> dict:
        """Start complete streaming pipeline from browser to Cast.

        Orchestrates all components in sequence:
        1. Discover Cast device
        2. Start Xvfb virtual display
        3. Launch browser with authentication
        4. Start FFmpeg encoding
        5. Start Cast session
        6. Stream for configured duration or indefinitely

        Returns:
            Dictionary with status, stream_url, device info, and duration

        Raises:
            ValueError: If Cast device not found
            RuntimeError: If any component fails to start
        """
        logger.info("Starting complete streaming pipeline...")

        try:
            # Get quality configuration
            quality = get_quality_config(self.quality_preset)
            logger.info(
                f"Using quality preset '{self.quality_preset}': "
                f"{quality.resolution[0]}x{quality.resolution[1]} @ {quality.bitrate}kbps"
            )

            # Discover Cast device
            logger.info(f"Discovering Cast device: {self.cast_device_name}")
            cast_device = await get_cast_device(self.cast_device_name)
            if not cast_device:
                raise ValueError(f"Cast device not found: {self.cast_device_name}")

            device_name = get_device_name(cast_device)
            logger.info(f"Found Cast device: {device_name}")

            # Start Xvfb virtual display
            logger.info("Starting Xvfb virtual display...")
            async with XvfbManager(resolution=quality.resolution) as display:
                logger.info(f"Xvfb started on display {display}")

                # Launch browser with auth
                logger.info("Launching browser...")
                async with BrowserManager() as browser:
                    logger.info(f"Navigating to {self.url}")
                    page = await browser.get_page(self.url)

                    # Inject authentication if provided
                    if self.auth_config:
                        logger.info("Injecting authentication...")
                        await inject_auth(page, self.url, self.auth_config)

                    # Wait for page to load
                    logger.info("Waiting for page to load...")
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    logger.info("Page loaded successfully")

                    # Start FFmpeg encoding
                    logger.info("Starting FFmpeg encoder...")
                    async with FFmpegEncoder(quality, display=display, mode=self.mode) as stream_url:
                        logger.info(f"FFmpeg encoding started: {stream_url}")

                        # Start Cast session
                        logger.info("Starting Cast session...")
                        async with CastSessionManager(cast_device) as cast_session:
                            logger.info(f"Cast session active: {device_name}")

                            # Start playback on Cast device
                            logger.info(f"Starting playback: {stream_url}")
                            cast_session.start_cast(stream_url, mode=self.mode)

                            # If duration specified, wait for timeout
                            if self.duration:
                                logger.info(
                                    f"Streaming for {self.duration} seconds..."
                                )
                                await asyncio.sleep(self.duration)
                                logger.info("Duration reached, stopping stream")
                            else:
                                # Stream indefinitely (until external stop signal)
                                logger.info(
                                    "Streaming indefinitely (no duration set). "
                                    "Use stop_stream() to terminate."
                                )
                                # Placeholder for Phase 4 webhook stop
                                await asyncio.sleep(float('inf'))

            logger.info("Streaming pipeline completed successfully")

            return {
                "status": "completed",
                "stream_url": stream_url,
                "device": device_name,
                "duration": self.duration
            }

        except Exception as e:
            logger.error(f"Streaming failed: {e}", exc_info=True)
            raise

    async def stop_stream(self):
        """Stop active stream (placeholder for Phase 4).

        This method is a placeholder for Phase 4 webhook-triggered stop.
        Currently, duration timeout handles auto-stop. In Phase 4, this
        will use asyncio.Event to signal stop and break out of indefinite stream.

        Note:
            When streaming with duration=None, the stream runs indefinitely
            until the context managers exit (which currently never happens).
            Phase 4 will implement proper stop signaling via webhooks.
        """
        logger.info("stop_stream called (placeholder for Phase 4)")
        logger.info(
            "Currently, streams with duration=None run indefinitely. "
            "Phase 4 will implement webhook-triggered stop via asyncio.Event."
        )
