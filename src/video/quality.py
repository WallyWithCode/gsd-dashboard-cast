"""Video quality configuration for FFmpeg encoding.

Provides configurable quality presets for different streaming scenarios:
- 1080p: High quality for detailed dashboards
- 720p: Balanced quality and performance
- low-latency: Optimized for minimal delay
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class QualityConfig:
    """Configuration for video encoding quality settings.

    Attributes:
        resolution: Video resolution as (width, height) tuple
        bitrate: Target bitrate in kbps
        framerate: Target framerate (default 30fps)
        preset: FFmpeg encoding speed preset (ultrafast, fast, medium)
        latency_mode: Encoding optimization mode ('low' or 'normal')
    """
    resolution: tuple[int, int]
    bitrate: int
    framerate: int = 30
    preset: Literal['ultrafast', 'fast', 'medium'] = 'medium'
    latency_mode: Literal['low', 'normal'] = 'normal'


# Quality presets based on research recommendations
# 1080p: High quality for detailed dashboards with normal latency
# 720p: Balanced quality/performance with normal latency
# low-latency: Optimized for minimal delay with reduced quality
QUALITY_PRESETS: dict[str, QualityConfig] = {
    '1080p': QualityConfig(
        resolution=(1920, 1080),
        bitrate=5000,
        framerate=30,
        preset='medium',
        latency_mode='normal'
    ),
    '720p': QualityConfig(
        resolution=(1280, 720),
        bitrate=2500,
        framerate=30,
        preset='fast',
        latency_mode='normal'
    ),
    'low-latency': QualityConfig(
        resolution=(1280, 720),
        bitrate=2000,
        framerate=30,
        preset='ultrafast',
        latency_mode='low'
    ),
}


def get_quality_config(preset_name: str) -> QualityConfig:
    """Get quality configuration by preset name.

    Args:
        preset_name: Name of the quality preset ('1080p', '720p', 'low-latency')

    Returns:
        QualityConfig for the requested preset

    Raises:
        ValueError: If preset_name is not recognized
    """
    if preset_name not in QUALITY_PRESETS:
        available = ', '.join(QUALITY_PRESETS.keys())
        raise ValueError(
            f"Unknown quality preset: {preset_name}. "
            f"Available presets: {available}"
        )

    return QUALITY_PRESETS[preset_name]
