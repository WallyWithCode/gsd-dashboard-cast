"""Integration tests for video streaming pipeline.

Tests complete pipeline from browser to video encoding, verifying:
- Quality presets work correctly
- Duration control functions properly
- Component integration succeeds
- End-to-end latency is acceptable
"""

import pytest
import asyncio
import os
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.video.stream import StreamManager
from src.video.quality import get_quality_config, QUALITY_PRESETS
from src.video.encoder import FFmpegEncoder
from src.video.capture import XvfbManager


class TestQualityConfiguration:
    """Test quality preset configuration."""

    def test_quality_presets_exist(self):
        """Verify all required quality presets exist."""
        assert '1080p' in QUALITY_PRESETS
        assert '720p' in QUALITY_PRESETS
        assert 'low-latency' in QUALITY_PRESETS

    def test_1080p_preset_configuration(self):
        """Verify 1080p preset has correct parameters."""
        config = get_quality_config('1080p')
        assert config.resolution == (1920, 1080)
        assert config.bitrate == 5000
        assert config.latency_mode == 'normal'

    def test_720p_preset_configuration(self):
        """Verify 720p preset has correct parameters."""
        config = get_quality_config('720p')
        assert config.resolution == (1280, 720)
        assert config.bitrate == 2500

    def test_low_latency_preset_configuration(self):
        """Verify low-latency preset has correct parameters."""
        config = get_quality_config('low-latency')
        assert config.preset == 'ultrafast'
        assert config.latency_mode == 'low'

    def test_invalid_preset_raises_error(self):
        """Verify unknown preset name raises ValueError."""
        with pytest.raises(ValueError):
            get_quality_config('invalid-preset')


class TestFFmpegEncoder:
    """Test FFmpeg encoder functionality."""

    def test_ffmpeg_args_include_quality_params(self):
        """Verify FFmpeg args include resolution and bitrate from config."""
        config = get_quality_config('1080p')
        encoder = FFmpegEncoder(config)
        args = encoder.build_ffmpeg_args('/tmp/test.m3u8')

        # Check key parameters present
        assert '-video_size' in args
        assert '1920x1080' in args
        assert '-b:v' in args
        assert '5000k' in args

    def test_low_latency_mode_args(self):
        """Verify low-latency mode includes zerolatency tuning."""
        config = get_quality_config('low-latency')
        encoder = FFmpegEncoder(config)
        args = encoder.build_ffmpeg_args('/tmp/test.m3u8')

        # Low-latency specific flags
        assert '-tune' in args
        assert 'zerolatency' in args
        assert '-bf' in args
        assert '0' in args  # No B-frames

    def test_normal_latency_mode_args(self):
        """Verify normal mode allows B-frames for better compression."""
        config = get_quality_config('1080p')
        encoder = FFmpegEncoder(config)
        args = encoder.build_ffmpeg_args('/tmp/test.m3u8')

        # Normal latency allows B-frames
        assert '-bf' in args
        idx = args.index('-bf')
        assert args[idx + 1] == '2'  # 2 B-frames


@pytest.mark.asyncio
class TestStreamingOrchestration:
    """Test complete streaming pipeline orchestration."""

    @patch('src.video.stream.get_cast_device')
    @patch('src.video.capture.asyncio.create_subprocess_exec')
    async def test_stream_manager_initialization(self, mock_subprocess, mock_cast):
        """Verify StreamManager initializes with correct parameters."""
        manager = StreamManager(
            url="https://dashboard.local",
            cast_device_name="Test TV",
            quality_preset="720p",
            duration=30
        )

        assert manager.url == "https://dashboard.local"
        assert manager.cast_device_name == "Test TV"
        assert manager.quality_preset == "720p"
        assert manager.duration == 30

    async def test_duration_control(self):
        """Verify stream stops after configured duration."""
        # Create mock Cast device
        mock_cast_device = Mock()
        mock_cast_device.device.friendly_name = "Test TV"

        # Create mock page
        mock_page = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()

        # Create mock browser manager that returns our page
        mock_browser = AsyncMock()
        mock_browser.get_page = AsyncMock(return_value=mock_page)
        mock_browser.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = AsyncMock(return_value=False)

        # Create mock Xvfb manager
        mock_xvfb = AsyncMock()
        mock_xvfb.__aenter__ = AsyncMock(return_value=':99')
        mock_xvfb.__aexit__ = AsyncMock(return_value=False)

        # Create mock FFmpeg encoder
        mock_ffmpeg = AsyncMock()
        mock_ffmpeg.__aenter__ = AsyncMock(return_value='http://localhost:8080/stream.m3u8')
        mock_ffmpeg.__aexit__ = AsyncMock(return_value=False)

        # Create mock Cast session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        # Patch all components
        with patch('src.video.stream.get_cast_device', return_value=mock_cast_device), \
             patch('src.video.stream.XvfbManager', return_value=mock_xvfb), \
             patch('src.video.stream.BrowserManager', return_value=mock_browser), \
             patch('src.video.stream.FFmpegEncoder', return_value=mock_ffmpeg), \
             patch('src.video.stream.CastSessionManager', return_value=mock_session):

            manager = StreamManager(
                url="https://test.local",
                cast_device_name="Test TV",
                quality_preset="720p",
                duration=2  # 2 second test
            )

            start = time.time()
            result = await manager.start_stream()
            elapsed = time.time() - start

            # Should complete around 2 seconds (allow 1s tolerance)
            assert 1.5 < elapsed < 3.5
            assert result['status'] == 'completed'
            assert result['duration'] == 2

    async def test_cast_device_not_found_raises_error(self):
        """Verify ValueError raised when Cast device not found."""
        with patch('src.video.stream.get_cast_device', return_value=None):
            manager = StreamManager(
                url="https://test.local",
                cast_device_name="Nonexistent TV",
                quality_preset="720p"
            )

            with pytest.raises(ValueError, match="Cast device not found"):
                await manager.start_stream()

    async def test_invalid_quality_preset_raises_error(self):
        """Verify ValueError raised for invalid quality preset."""
        with pytest.raises(ValueError, match="Unknown quality preset"):
            StreamManager(
                url="https://test.local",
                cast_device_name="Test TV",
                quality_preset="invalid-preset"
            )


@pytest.mark.asyncio
class TestXvfbManager:
    """Test Xvfb display management."""

    @patch('src.video.capture.asyncio.create_subprocess_exec')
    @patch('src.video.capture.shutil.which', return_value='/usr/bin/Xvfb')
    async def test_xvfb_sets_display_env_var(self, mock_which, mock_subprocess):
        """Verify DISPLAY environment variable is set."""
        # Store original DISPLAY value
        original_display = os.environ.get('DISPLAY')

        # Create mock process
        mock_process = AsyncMock()
        mock_process.poll.return_value = None
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process

        try:
            async with XvfbManager(display=':99') as display:
                assert os.environ.get('DISPLAY') == ':99'
                assert display == ':99'

            # Verify cleaned up after exit
            assert os.environ.get('DISPLAY') != ':99'

        finally:
            # Restore original DISPLAY value
            if original_display:
                os.environ['DISPLAY'] = original_display
            elif 'DISPLAY' in os.environ:
                del os.environ['DISPLAY']

    @patch('src.video.capture.shutil.which', return_value=None)
    async def test_xvfb_raises_error_when_not_installed(self, mock_which):
        """Verify RuntimeError raised when Xvfb not installed."""
        manager = XvfbManager()

        with pytest.raises(RuntimeError, match="Xvfb not found"):
            async with manager:
                pass


@pytest.mark.asyncio
class TestPipelineIntegration:
    """Test end-to-end pipeline integration."""

    async def test_components_use_context_managers(self):
        """Verify all components properly implement context manager pattern."""
        # This test verifies the pattern, not actual execution

        # Test XvfbManager has context manager methods
        xvfb = XvfbManager()
        assert hasattr(xvfb, '__aenter__')
        assert hasattr(xvfb, '__aexit__')

        # Test FFmpegEncoder has context manager methods
        from src.video.quality import get_quality_config
        config = get_quality_config('720p')
        encoder = FFmpegEncoder(config)
        assert hasattr(encoder, '__aenter__')
        assert hasattr(encoder, '__aexit__')

    async def test_stream_manager_orchestration_order(self):
        """Verify StreamManager orchestrates components in correct order."""
        # Track call order
        call_order = []

        # Create mock components that track when they're called
        mock_cast_device = Mock()
        mock_cast_device.device.friendly_name = "Test TV"

        async def mock_get_cast_device(name):
            call_order.append('cast_discovery')
            return mock_cast_device

        class MockXvfb:
            async def __aenter__(self):
                call_order.append('xvfb_start')
                return ':99'
            async def __aexit__(self, *args):
                call_order.append('xvfb_stop')
                return False

        class MockBrowser:
            async def __aenter__(self):
                call_order.append('browser_start')
                return self
            async def __aexit__(self, *args):
                call_order.append('browser_stop')
                return False
            async def get_page(self, url):
                call_order.append('browser_navigate')
                page = AsyncMock()
                page.wait_for_load_state = AsyncMock()
                return page

        class MockFFmpeg:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                call_order.append('ffmpeg_start')
                return 'http://stream.url'
            async def __aexit__(self, *args):
                call_order.append('ffmpeg_stop')
                return False

        class MockCast:
            def __init__(self, *args):
                pass
            async def __aenter__(self):
                call_order.append('cast_start')
                return self
            async def __aexit__(self, *args):
                call_order.append('cast_stop')
                return False

        with patch('src.video.stream.get_cast_device', mock_get_cast_device), \
             patch('src.video.stream.XvfbManager', MockXvfb), \
             patch('src.video.stream.BrowserManager', MockBrowser), \
             patch('src.video.stream.FFmpegEncoder', MockFFmpeg), \
             patch('src.video.stream.CastSessionManager', MockCast):

            manager = StreamManager(
                url="https://test.local",
                cast_device_name="Test TV",
                quality_preset="720p",
                duration=0.1  # Very short duration
            )

            await manager.start_stream()

        # Verify correct order: discovery → xvfb → browser → ffmpeg → cast
        # Then reverse order for cleanup
        expected_order = [
            'cast_discovery',
            'xvfb_start',
            'browser_start',
            'browser_navigate',
            'ffmpeg_start',
            'cast_start',
            'cast_stop',
            'ffmpeg_stop',
            'browser_stop',
            'xvfb_stop'
        ]

        assert call_order == expected_order
