"""Browser lifecycle management with Playwright.

Provides a context manager for launching headless Chrome, managing browser
instances, and ensuring proper resource cleanup to prevent memory leaks.
"""

from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import logging

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser lifecycle with automatic cleanup.

    Usage:
        async with BrowserManager() as manager:
            page = await manager.get_page("https://example.com")
            # Use page...
        # Browser automatically cleaned up on exit
    """

    def __init__(self):
        """Initialize browser manager."""
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self):
        """Enter context manager - launch browser."""
        logger.info("Launching browser...")
        self.playwright = await async_playwright().start()

        # Launch headless Chrome with minimal resource usage
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',  # Prevent shared memory issues in Docker
                '--disable-gpu',
            ]
        )

        # Create browser context with viewport
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=False,  # Enforce HTTPS security
        )

        logger.info("Browser launched successfully")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - clean up resources."""
        logger.info("Cleaning up browser resources...")

        try:
            if self.context:
                await self.context.close()
                logger.debug("Browser context closed")
        except Exception as e:
            logger.warning(f"Error closing context: {e}")

        try:
            if self.browser:
                await self.browser.close()
                logger.debug("Browser closed")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

        try:
            if self.playwright:
                await self.playwright.stop()
                logger.debug("Playwright stopped")
        except Exception as e:
            logger.warning(f"Error stopping playwright: {e}")

        logger.info("Browser cleanup complete")
        # Don't suppress exceptions
        return False

    async def get_page(
        self,
        url: str,
        auth: Optional[Dict[str, Any]] = None
    ) -> Page:
        """Navigate to URL with optional authentication.

        Args:
            url: Target URL to load
            auth: Optional authentication dict with:
                - cookies: Dict of cookie name->value pairs
                - localStorage: Dict of localStorage key->value pairs
                - domain: Domain for cookies (extracted from URL if not provided)

        Returns:
            Page object ready for interaction

        Raises:
            ValueError: If browser not initialized
        """
        if not self.context:
            raise ValueError("Browser not initialized. Use 'async with' context manager.")

        logger.info(f"Creating new page for {url}")
        page = await self.context.new_page()

        # Inject authentication if provided
        if auth:
            from .auth import inject_auth
            await inject_auth(page, url, auth)

        # Navigate to URL
        logger.info(f"Navigating to {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)

        return page
