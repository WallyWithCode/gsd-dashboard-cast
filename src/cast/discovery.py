"""Cast device discovery via mDNS.

Provides functions to discover Cast-enabled devices on the local network
using pychromecast's built-in mDNS discovery.
"""

from typing import List, Optional
import asyncio
import logging
import pychromecast

logger = logging.getLogger(__name__)


async def discover_devices(timeout: int = 5) -> List[pychromecast.Chromecast]:
    """Discover Cast devices on the local network via mDNS.

    Args:
        timeout: Discovery duration in seconds (default: 5)

    Returns:
        List of discovered Chromecast objects (may be empty)

    Note:
        This wraps pychromecast's blocking discovery in asyncio to maintain
        async/await patterns from Phase 1.
    """
    logger.info(f"Starting Cast device discovery (timeout: {timeout}s)...")

    try:
        # Run blocking discovery in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        chromecasts, browser = await loop.run_in_executor(
            None,
            lambda: pychromecast.get_chromecasts(timeout=timeout)
        )

        if chromecasts:
            logger.info(f"Discovered {len(chromecasts)} Cast device(s):")
            for cc in chromecasts:
                logger.info(f"  - {cc.device.friendly_name} ({cc.device.model_name}) at {cc.host}:{cc.port} [uuid: {cc.uuid}]")
        else:
            logger.warning("No Cast devices found on network")

        # Stop the browser to clean up mDNS
        if browser:
            browser.stop_discovery()

        return chromecasts

    except Exception as e:
        logger.error(f"Error during Cast device discovery: {e}")
        # Return empty list instead of raising - caller handles missing devices
        return []


async def get_cast_device(
    device_name: Optional[str] = None,
    timeout: int = 5
) -> Optional[pychromecast.Chromecast]:
    """Get a specific Cast device or the first available device.

    Args:
        device_name: Friendly name of device to find (None = first device)
        timeout: Discovery duration in seconds (default: 5)

    Returns:
        Chromecast object if found, None otherwise

    Example:
        # Get specific device
        device = await get_cast_device("Living Room TV")

        # Get any available device
        device = await get_cast_device()
    """
    devices = await discover_devices(timeout)

    if not devices:
        logger.warning("No Cast devices available")
        return None

    # If no device name specified, return first discovered
    if device_name is None:
        selected = devices[0]
        logger.info(f"Selected first available device: {selected.device.friendly_name}")
        return selected

    # Search for device by friendly name
    for device in devices:
        if device.device.friendly_name.lower() == device_name.lower():
            logger.info(f"Found requested device: {device.device.friendly_name}")
            return device

    logger.warning(f"Device '{device_name}' not found among {len(devices)} discovered device(s)")
    return None
