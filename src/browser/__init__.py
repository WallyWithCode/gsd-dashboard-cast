"""Browser automation module for Dashboard Cast Service.

This module provides Playwright-based browser automation with authentication
injection and proper resource management.
"""

from .manager import BrowserManager
from .auth import inject_auth

__all__ = ["BrowserManager", "inject_auth"]
