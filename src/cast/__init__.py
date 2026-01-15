"""Cast protocol integration for Android TV.

Provides device discovery via mDNS and session management for casting
video streams to Cast-enabled devices.
"""

from .discovery import discover_devices, get_cast_device
from .session import CastSessionManager

__all__ = [
    'discover_devices',
    'get_cast_device',
    'CastSessionManager',
]
