"""Network utilities for Cast device accessibility.

This module provides utilities to detect the host IP address that Cast devices
can use to access HTTP streams served by this application. The IP must be
reachable from the local network, not localhost/127.0.0.1.
"""

import os
import socket

import structlog

logger = structlog.get_logger()


def get_host_ip() -> str:
    """Get the host IP address accessible from the local network.

    Attempts to determine the LAN-accessible IP address for this host.
    This IP is used to construct HTTP URLs that Cast devices can access
    to retrieve HLS playlists and video segments.

    The function tries these methods in order:
    1. STREAM_HOST_IP environment variable (for Docker/manual override)
    2. Resolve the hostname to an IP address
    3. If that fails or returns localhost, connect to an external IP
       (8.8.8.8) and get the local socket address

    Returns:
        IP address string (e.g., "192.168.1.100")

    Note:
        Returns "127.0.0.1" only if all methods fail to find a LAN address.
        This would indicate a network configuration issue.

    Environment Variables:
        STREAM_HOST_IP: Manual override for host IP (required for Docker)
    """
    # Method 0: Check for manual override (needed for Docker)
    override_ip = os.getenv("STREAM_HOST_IP")
    if override_ip:
        logger.info("host_ip_from_env", ip=override_ip)
        return override_ip

    ip = None

    # Method 1: Try hostname resolution
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        logger.debug("host_ip_from_hostname", hostname=hostname, ip=ip)
    except socket.error as e:
        logger.debug("hostname_resolution_failed", error=str(e))

    # If we got localhost or resolution failed, try socket connection method
    if ip is None or ip.startswith("127."):
        try:
            # Create a socket and connect to external IP (doesn't send data)
            # This reveals our outbound IP address
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Use Google DNS as target (port doesn't matter for UDP)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                logger.debug("host_ip_from_socket", ip=ip)
        except socket.error as e:
            logger.warning("socket_method_failed", error=str(e))
            # Fall back to localhost if all methods fail
            if ip is None:
                ip = "127.0.0.1"
                logger.warning("using_localhost_fallback", ip=ip)

    logger.info("host_ip_detected", ip=ip)
    return ip
