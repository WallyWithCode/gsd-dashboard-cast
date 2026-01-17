"""Video capture and encoding module for dashboard casting.

This module provides Xvfb virtual display management, FFmpeg-based video encoding
with configurable quality presets, and HTTP streaming server for serving video
streams to Cast devices.
"""

from .capture import XvfbManager
from .network import get_host_ip
from .server import StreamingServer

__all__ = [
    "XvfbManager",
    "get_host_ip",
    "StreamingServer",
]
