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


def get_device_name(device: pychromecast.Chromecast) -> str:
    """Get a friendly name for a Cast device.

    Handles both mDNS-discovered devices (cast_info populated) and
    direct IP connections (cast_info.friendly_name may be None).
    """
    # Try cast_info.friendly_name first (pychromecast 14.x)
    if hasattr(device, 'cast_info') and device.cast_info:
        if device.cast_info.friendly_name:
            return device.cast_info.friendly_name
        # Fall back to host IP
        if device.cast_info.host:
            return f"Cast@{device.cast_info.host}"
    # Try device.device.friendly_name (older pychromecast)
    if hasattr(device, 'device') and device.device:
        if hasattr(device.device, 'friendly_name') and device.device.friendly_name:
            return device.device.friendly_name
    # Last resort: use name or host
    if hasattr(device, 'name') and device.name:
        return device.name
    if hasattr(device, 'host') and device.host:
        return f"Cast@{device.host}"
    return "Unknown Cast Device"


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
                name = get_device_name(cc)
                model = cc.model_name or "Unknown"
                host = cc.cast_info.host if hasattr(cc, 'cast_info') and cc.cast_info else cc.host
                port = cc.cast_info.port if hasattr(cc, 'cast_info') and cc.cast_info else cc.port
                logger.info(f"  - {name} ({model}) at {host}:{port} [uuid: {cc.uuid}]")
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
            # Connect directly to known IP using get_chromecast_from_host
            loop = asyncio.get_event_loop()

            def connect_to_host():
                # Tuple: (host, port, uuid, model_name, friendly_name)
                host_tuple = (static_ip, None, None, None, None)
                cc = pychromecast.get_chromecast_from_host(host_tuple)
                # Wait for connection with timeout (default wait() blocks forever)
                cc.wait(timeout=10)
                return cc

            device = await loop.run_in_executor(None, connect_to_host)

            if device and device.socket_client:
                friendly_name = get_device_name(device)
                logger.info(f"Connected to Cast device at {static_ip}: {friendly_name}")
                return device
            else:
                logger.warning(f"Failed to connect to Cast device at {static_ip}, falling back to mDNS discovery")

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
        logger.info(f"Selected first available device: {get_device_name(selected)}")
        return selected

    # Search for device by friendly name
    for device in devices:
        found_name = get_device_name(device)
        if found_name.lower() == device_name.lower():
            logger.info(f"Found requested device: {found_name}")
            return device

    logger.warning(f"Device '{device_name}' not found among {len(devices)} discovered device(s)")
    return None
