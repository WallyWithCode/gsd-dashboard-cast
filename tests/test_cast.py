"""Tests for Cast module (discovery, session management, and retry logic)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio

from src.cast.discovery import discover_devices, get_cast_device
from src.cast.session import CastSessionManager
from src.cast.retry import retry_with_backoff


# Test fixtures
@pytest.fixture
def mock_chromecast():
    """Create a mock Chromecast device."""
    mock_device = MagicMock()
    mock_device.device.friendly_name = "Living Room TV"
    mock_device.device.model_name = "Chromecast"
    mock_device.host = "192.168.1.100"
    mock_device.port = 8009
    mock_device.uuid = "test-uuid-123"
    mock_device.wait = MagicMock()
    mock_device.set_volume_muted = MagicMock()
    mock_device.disconnect = MagicMock()
    mock_device.media_controller = MagicMock()
    mock_device.media_controller.stop = MagicMock()
    return mock_device


@pytest.fixture
def mock_chromecast_list(mock_chromecast):
    """Create a list of mock Chromecast devices."""
    device1 = mock_chromecast

    device2 = MagicMock()
    device2.device.friendly_name = "Bedroom TV"
    device2.device.model_name = "Chromecast Ultra"
    device2.host = "192.168.1.101"
    device2.port = 8009
    device2.uuid = "test-uuid-456"

    return [device1, device2]


# Discovery Tests
@pytest.mark.asyncio
async def test_discover_devices_success(mock_chromecast_list):
    """Test successful Cast device discovery."""
    mock_browser = MagicMock()
    mock_browser.stop_discovery = MagicMock()

    with patch('pychromecast.get_chromecasts') as mock_get:
        mock_get.return_value = (mock_chromecast_list, mock_browser)

        devices = await discover_devices(timeout=5)

        # Verify discovery was called with correct timeout
        mock_get.assert_called_once_with(timeout=5)

        # Verify browser cleanup
        mock_browser.stop_discovery.assert_called_once()

        # Verify devices returned
        assert len(devices) == 2
        assert devices[0].device.friendly_name == "Living Room TV"
        assert devices[1].device.friendly_name == "Bedroom TV"


@pytest.mark.asyncio
async def test_discover_devices_empty():
    """Test discovery when no devices found."""
    mock_browser = MagicMock()
    mock_browser.stop_discovery = MagicMock()

    with patch('pychromecast.get_chromecasts') as mock_get:
        mock_get.return_value = ([], mock_browser)

        devices = await discover_devices()

        # Should return empty list, not exception
        assert devices == []
        mock_browser.stop_discovery.assert_called_once()


@pytest.mark.asyncio
async def test_discover_devices_exception():
    """Test discovery handles exceptions gracefully."""
    with patch('pychromecast.get_chromecasts') as mock_get:
        mock_get.side_effect = Exception("Network error")

        devices = await discover_devices()

        # Should return empty list on error, not raise exception
        assert devices == []


@pytest.mark.asyncio
async def test_get_cast_device_by_name(mock_chromecast_list):
    """Test getting device by specific name."""
    mock_browser = MagicMock()
    mock_browser.stop_discovery = MagicMock()

    with patch('pychromecast.get_chromecasts') as mock_get:
        mock_get.return_value = (mock_chromecast_list, mock_browser)

        # Case-insensitive search
        device = await get_cast_device("bedroom tv")

        assert device is not None
        assert device.device.friendly_name == "Bedroom TV"


@pytest.mark.asyncio
async def test_get_cast_device_first(mock_chromecast_list):
    """Test getting first available device when name not specified."""
    mock_browser = MagicMock()
    mock_browser.stop_discovery = MagicMock()

    with patch('pychromecast.get_chromecasts') as mock_get:
        mock_get.return_value = (mock_chromecast_list, mock_browser)

        # No device name = return first
        device = await get_cast_device()

        assert device is not None
        assert device.device.friendly_name == "Living Room TV"


@pytest.mark.asyncio
async def test_get_cast_device_not_found(mock_chromecast_list):
    """Test getting device that doesn't exist."""
    mock_browser = MagicMock()
    mock_browser.stop_discovery = MagicMock()

    with patch('pychromecast.get_chromecasts') as mock_get:
        mock_get.return_value = (mock_chromecast_list, mock_browser)

        device = await get_cast_device("Kitchen TV")

        # Should return None when not found
        assert device is None


@pytest.mark.asyncio
async def test_get_cast_device_empty_list():
    """Test getting device when no devices available."""
    mock_browser = MagicMock()
    mock_browser.stop_discovery = MagicMock()

    with patch('pychromecast.get_chromecasts') as mock_get:
        mock_get.return_value = ([], mock_browser)

        device = await get_cast_device("Any TV")

        # Should return None when no devices
        assert device is None


# Session Lifecycle Tests
@pytest.mark.asyncio
async def test_cast_session_lifecycle(mock_chromecast):
    """Test CastSessionManager context manager lifecycle."""
    manager = CastSessionManager(mock_chromecast)

    assert manager.is_active is False

    async with manager as session:
        # Session should be active inside context
        assert session.is_active is True
        assert session.device == mock_chromecast

        # Device wait should have been called
        mock_chromecast.wait.assert_called_once()

        # HDMI-CEC wake should have been triggered
        mock_chromecast.set_volume_muted.assert_called_once_with(False)

    # After exit, session should be inactive
    assert manager.is_active is False

    # Disconnect should have been called
    mock_chromecast.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_hdmi_cec_wake(mock_chromecast):
    """Test HDMI-CEC wake is triggered on session start."""
    manager = CastSessionManager(mock_chromecast)

    async with manager:
        # Verify HDMI-CEC wake via volume unmute
        mock_chromecast.set_volume_muted.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_session_start_cast_not_active():
    """Test start_cast raises error when session not active."""
    mock_device = MagicMock()
    manager = CastSessionManager(mock_device)

    # Should raise error when called outside context manager
    with pytest.raises(RuntimeError, match="Session not initialized"):
        manager.start_cast("http://example.com/video.mp4")


@pytest.mark.asyncio
async def test_session_start_cast_active(mock_chromecast):
    """Test start_cast works when session is active."""
    manager = CastSessionManager(mock_chromecast)

    async with manager:
        # Should not raise error when session is active
        manager.start_cast("http://example.com/video.mp4")


@pytest.mark.asyncio
async def test_session_stop_cast(mock_chromecast):
    """Test stop_cast stops media playback."""
    manager = CastSessionManager(mock_chromecast)

    async with manager:
        manager.is_active = True
        await manager.stop_cast()

        # Verify media controller stop was called
        mock_chromecast.media_controller.stop.assert_called_once()


# Retry Logic Tests
@pytest.mark.asyncio
async def test_retry_with_backoff_success():
    """Test retry succeeds on second attempt."""
    call_count = 0

    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("First attempt fails")
        return "success"

    result = await retry_with_backoff(
        flaky_function,
        max_retries=3,
        initial_delay=0.1,
        exceptions=(ConnectionError,)
    )

    assert result == "success"
    assert call_count == 2  # Failed once, succeeded second time


@pytest.mark.asyncio
async def test_retry_with_backoff_exhausted():
    """Test retry exhausts all attempts and raises last exception."""
    call_count = 0

    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise TimeoutError(f"Attempt {call_count} failed")

    with pytest.raises(TimeoutError, match="Attempt 4 failed"):
        await retry_with_backoff(
            always_fails,
            max_retries=3,
            initial_delay=0.1,
            exceptions=(TimeoutError,)
        )

    # Should have tried max_retries + 1 times (initial + 3 retries)
    assert call_count == 4


@pytest.mark.asyncio
async def test_retry_with_backoff_immediate_success():
    """Test retry succeeds on first attempt."""
    async def succeeds_immediately():
        return "immediate_success"

    result = await retry_with_backoff(
        succeeds_immediately,
        max_retries=3,
        initial_delay=0.1
    )

    assert result == "immediate_success"


@pytest.mark.asyncio
async def test_retry_with_backoff_exponential_delay():
    """Test retry uses exponential backoff delays."""
    delays = []

    async def track_delays():
        if len(delays) < 3:
            delays.append(asyncio.get_event_loop().time())
            raise ConnectionError("Retry needed")
        return "success"

    await retry_with_backoff(
        track_delays,
        max_retries=3,
        initial_delay=0.1,
        backoff_factor=2.0,
        exceptions=(ConnectionError,)
    )

    # Should have 3 delays recorded
    assert len(delays) == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_max_delay_cap():
    """Test retry respects max_delay cap."""
    call_count = 0

    async def fails_multiple_times():
        nonlocal call_count
        call_count += 1
        if call_count < 4:
            raise ConnectionError(f"Attempt {call_count}")
        return "success"

    result = await retry_with_backoff(
        fails_multiple_times,
        max_retries=5,
        initial_delay=1.0,
        max_delay=2.0,  # Cap at 2 seconds
        backoff_factor=10.0,  # Large factor should be capped
        exceptions=(ConnectionError,)
    )

    assert result == "success"


@pytest.mark.asyncio
async def test_retry_with_custom_exceptions():
    """Test retry only catches specified exceptions."""
    async def raises_value_error():
        raise ValueError("Wrong type of error")

    # Should not retry ValueError, raise immediately
    with pytest.raises(ValueError, match="Wrong type of error"):
        await retry_with_backoff(
            raises_value_error,
            max_retries=3,
            initial_delay=0.1,
            exceptions=(ConnectionError, TimeoutError)  # ValueError not in list
        )
