"""Cast device discovery via mDNS.

Provides functions to discover Cast-enabled devices on the local network
using pychromecast's built-in mDNS discovery.

Environment variables:
    CAST_DEVICE_IP: Static IP address for Cast device (bypasses mDNS discovery).
                    Useful for WSL2 environments where mDNS doesn't work.
    CAST_DEVICE_NAME: Friendly name of Cast device to discover.
"""

from typing import List, Optional
import asyncio
import logging
import os
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

    Checks CAST_DEVICE_IP environment variable first for static IP configuration.
    If set, attempts connection to that IP before falling back to mDNS discovery.

    This is useful for WSL2 environments where mDNS doesn't work due to
    virtualized NAT network limitations.

    Args:
        device_name: Friendly name of device to find (None = first device)
        timeout: Discovery duration in seconds (default: 5)

    Returns:
        Chromecast object if found, None otherwise

    Environment Variables:
        CAST_DEVICE_IP: Static IP address of Cast device (bypasses mDNS)
        CAST_DEVICE_NAME: Alternative to device_name parameter

    Example:
        # Get specific device
        device = await get_cast_device("Living Room TV")

        # Get any available device
        device = await get_cast_device()

        # Use static IP from environment
        # export CAST_DEVICE_IP=10.10.0.31
        device = await get_cast_device()
    """
    # Check for static IP configuration first
    static_ip = os.getenv("CAST_DEVICE_IP")
    if static_ip:
        logger.info(f"Using static Cast device IP from CAST_DEVICE_IP environment variable: {static_ip}")
        try:
            # Run blocking get_chromecast_from_host in executor
            loop = asyncio.get_event_loop()
            chromecasts, browser = await loop.run_in_executor(
                None,
                lambda: pychromecast.get_chromecasts(hosts=[static_ip])
            )

            if chromecasts and len(chromecasts) > 0:
                device = chromecasts[0]
                logger.info(f"Connected to Cast device at {static_ip}: {device.device.friendly_name}")

                # Stop the browser to clean up
                if browser:
                    browser.stop_discovery()

                return device
            else:
                logger.warning(f"Failed to connect to Cast device at {static_ip}, falling back to mDNS discovery")

                # Clean up browser if created
                if browser:
                    browser.stop_discovery()

        except Exception as e:
            logger.warning(f"Error connecting to static IP {static_ip}: {e}, falling back to mDNS discovery")

    # Fall back to mDNS discovery
    # Check for device name from environment if not provided
    if device_name is None:
        device_name = os.getenv("CAST_DEVICE_NAME")

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
