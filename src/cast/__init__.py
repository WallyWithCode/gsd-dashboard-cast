"""Cast protocol integration for Android TV.

Provides device discovery via mDNS and session management for casting
video streams to Cast-enabled devices.

Features:
    - Cast device discovery via mDNS using pychromecast
    - Session management with context manager pattern
    - Exponential backoff retry for connection reliability
    - Automatic HDMI-CEC wake capability to turn on TV
    - Graceful error handling with async/await patterns

Basic Usage:
    ```python
    from src.cast import discover_devices, get_cast_device, CastSessionManager

    # Discover all Cast devices on network
    devices = await discover_devices(timeout=5)

    # Get specific device by name
    device = await get_cast_device("Living Room TV")

    # Or get first available device
    device = await get_cast_device()

    # Start Cast session with automatic cleanup
    async with CastSessionManager(device) as session:
        # TV is now awake via HDMI-CEC
        session.start_cast("http://example.com/video.mp4")
        # Session automatically cleaned up on exit
    ```

Advanced Usage with Retry:
    ```python
    from src.cast import retry_with_backoff

    # Wrap unreliable operations in retry logic
    async def connect_to_device():
        device = await get_cast_device("Living Room TV")
        if not device:
            raise ConnectionError("Device not found")
        return device

    device = await retry_with_backoff(
        connect_to_device,
        max_retries=3,
        initial_delay=1.0,
        exceptions=(ConnectionError, TimeoutError)
    )
    ```

Network Requirements:
    - Requires Docker host networking for mDNS discovery
    - Cast devices must be on same local network
    - No firewall blocking ports 5353 (mDNS) or 8009 (Cast)
"""

from .discovery import discover_devices, get_cast_device
from .session import CastSessionManager
from .retry import retry_with_backoff

__all__ = [
    'discover_devices',
    'get_cast_device',
    'CastSessionManager',
    'retry_with_backoff',
]
