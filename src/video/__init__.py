"""Video capture and encoding module for dashboard casting.

This module provides Xvfb virtual display management and FFmpeg-based video encoding
with configurable quality presets for streaming web content to Cast devices.
"""

from .capture import XvfbManager

__all__ = [
    "XvfbManager",
]

# Note: quality and encoder modules will be added in subsequent plans
