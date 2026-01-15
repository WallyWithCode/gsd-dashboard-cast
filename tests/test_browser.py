"""Tests for browser automation module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.browser.manager import BrowserManager
from src.browser.auth import inject_auth


@pytest.mark.asyncio
async def test_browser_manager_context_lifecycle():
    """Test browser launches and closes cleanly using context manager."""
    async with BrowserManager() as manager:
        # Verify browser is initialized
        assert manager.playwright is not None
        assert manager.browser is not None
        assert manager.context is not None

    # After exit, resources should be cleaned up
    # Note: We can't check if they're closed directly, but the context manager
    # should have called close() on all resources


@pytest.mark.asyncio
async def test_browser_manager_navigation():
    """Test page navigation to simple URL."""
    async with BrowserManager() as manager:
        page = await manager.get_page("https://example.com")

        # Verify page loaded
        assert page is not None
        title = await page.title()
        assert "Example" in title


@pytest.mark.asyncio
async def test_browser_manager_get_page_without_init():
    """Test that get_page raises error if browser not initialized."""
    manager = BrowserManager()

    # Should raise ValueError when browser not initialized
    with pytest.raises(ValueError, match="Browser not initialized"):
        await manager.get_page("https://example.com")


@pytest.mark.asyncio
async def test_inject_auth_cookies():
    """Test cookie injection into page context."""
    # Mock page and context
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.context = mock_context

    auth = {
        "cookies": {
            "session_id": "test123",
            "user_token": "abc789"
        }
    }

    await inject_auth(mock_page, "https://example.com", auth)

    # Verify cookies were added to context
    mock_context.add_cookies.assert_called_once()
    cookies = mock_context.add_cookies.call_args[0][0]

    assert len(cookies) == 2
    assert cookies[0]["name"] == "session_id"
    assert cookies[0]["value"] == "test123"
    assert cookies[0]["domain"] == "example.com"
    assert cookies[1]["name"] == "user_token"
    assert cookies[1]["value"] == "abc789"


@pytest.mark.asyncio
async def test_inject_auth_localstorage():
    """Test localStorage injection into page."""
    mock_page = AsyncMock()
    mock_page.context = AsyncMock()

    auth = {
        "localStorage": {
            "auth_token": "bearer_xyz",
            "user_id": "12345"
        }
    }

    await inject_auth(mock_page, "https://example.com", auth)

    # Verify init script was added
    mock_page.add_init_script.assert_called_once()
    script = mock_page.add_init_script.call_args[0][0]

    # Script should contain localStorage assignment
    assert "localStorage" in script
    assert "auth_token" in script
    assert "bearer_xyz" in script


@pytest.mark.asyncio
async def test_inject_auth_both_methods():
    """Test injection with both cookies and localStorage."""
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.context = mock_context

    auth = {
        "cookies": {"session": "abc"},
        "localStorage": {"token": "xyz"}
    }

    await inject_auth(mock_page, "https://example.com", auth)

    # Both methods should be called
    mock_context.add_cookies.assert_called_once()
    mock_page.add_init_script.assert_called_once()


@pytest.mark.asyncio
async def test_inject_auth_custom_domain():
    """Test cookie injection with custom domain override."""
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.context = mock_context

    auth = {
        "cookies": {"session": "test"},
        "domain": "custom.example.com"
    }

    await inject_auth(mock_page, "https://different.com", auth)

    # Verify custom domain was used
    mock_context.add_cookies.assert_called_once()
    cookies = mock_context.add_cookies.call_args[0][0]
    assert cookies[0]["domain"] == "custom.example.com"


@pytest.mark.asyncio
async def test_browser_manager_with_auth():
    """Test get_page with authentication."""
    async with BrowserManager() as manager:
        auth = {
            "cookies": {"test": "value"}
        }

        # This should inject auth and navigate
        page = await manager.get_page("https://example.com", auth=auth)

        # Verify page loaded
        assert page is not None
        title = await page.title()
        assert "Example" in title
