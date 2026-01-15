"""Authentication injection for browser sessions.

Supports cookie-based and localStorage-based authentication for accessing
protected dashboards.
"""

from typing import Dict, Any, Optional
from urllib.parse import urlparse
import json
import logging

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def inject_auth(page: Page, url: str, auth: Dict[str, Any]) -> None:
    """Inject authentication into page before navigation.

    Supports two authentication methods:
    1. Cookies: Standard session-based auth (Home Assistant, etc.)
    2. localStorage: Token-based auth (some dashboards use this)

    Args:
        page: Playwright Page object
        url: Target URL (used to extract domain for cookies)
        auth: Authentication dictionary with optional keys:
            - cookies: Dict[str, str] of name->value cookie pairs
            - localStorage: Dict[str, str] of key->value pairs
            - domain: Optional domain override for cookies

    Example:
        # Cookie-based auth
        auth = {
            "cookies": {
                "session_id": "abc123",
                "user_token": "xyz789"
            }
        }

        # localStorage-based auth
        auth = {
            "localStorage": {
                "auth_token": "bearer_token_here",
                "user_id": "12345"
            }
        }

        # Both methods
        auth = {
            "cookies": {"session": "abc123"},
            "localStorage": {"token": "xyz789"}
        }
    """
    cookies = auth.get("cookies", {})
    local_storage = auth.get("localStorage", {})

    # Extract domain from URL if not provided
    domain = auth.get("domain")
    if not domain:
        parsed = urlparse(url)
        domain = parsed.netloc

    # Inject cookies
    if cookies:
        logger.info(f"Injecting {len(cookies)} cookie(s) for domain {domain}")
        cookie_list = [
            {
                "name": name,
                "value": value,
                "domain": domain,
                "path": "/"
            }
            for name, value in cookies.items()
        ]
        await page.context.add_cookies(cookie_list)
        logger.debug(f"Cookies injected: {list(cookies.keys())}")

    # Inject localStorage via initialization script
    if local_storage:
        logger.info(f"Injecting {len(local_storage)} localStorage item(s)")
        # This script runs before page loads, setting up localStorage
        storage_json = json.dumps(local_storage)
        await page.add_init_script(f"Object.assign(window.localStorage, {storage_json})")
        logger.debug(f"localStorage injected: {list(local_storage.keys())}")
