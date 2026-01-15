"""Xvfb virtual display management for headless browser rendering.

Provides XvfbManager for lifecycle management of Xvfb virtual X11 display,
enabling headless browser rendering that can be captured by FFmpeg.
"""

import asyncio
import logging
import os
import shutil
from typing import Optional

logger = logging.getLogger(__name__)


class XvfbManager:
    """Manages Xvfb virtual display lifecycle.

    Provides a virtual X11 display for headless browser rendering that can
    be captured by FFmpeg. Ensures proper cleanup of Xvfb process on exit.

    Usage:
        async with XvfbManager(display=':99', resolution=(1920, 1080)) as manager:
            # DISPLAY environment variable set automatically
            # Launch browser here
        # Xvfb process cleaned up on exit

    Attributes:
        display: Display number (e.g., ':99')
        resolution: Tuple of (width, height) for display resolution
        depth: Color depth in bits (default: 24)
        process: Xvfb subprocess handle
    """

    def __init__(
        self,
        display: str = ':99',
        resolution: tuple[int, int] = (1920, 1080),
        depth: int = 24
    ):
        """Initialize Xvfb manager with display configuration.

        Args:
            display: Display number (e.g., ':99')
            resolution: Tuple of (width, height) for display resolution
            depth: Color depth in bits (default: 24)
        """
        self.display = display
        self.width, self.height = resolution
        self.depth = depth
        self.process: Optional[asyncio.subprocess.Process] = None

        logger.info(
            f"XvfbManager initialized: display={display}, "
            f"resolution={self.width}x{self.height}, depth={depth}"
        )

    async def __aenter__(self) -> str:
        """Start Xvfb process and configure display environment.

        Returns:
            Display string (e.g., ':99')

        Raises:
            RuntimeError: If Xvfb is not available or fails to start
        """
        # Check if Xvfb is available
        if not shutil.which('Xvfb'):
            raise RuntimeError(
                "Xvfb not found in PATH. "
                "Install with: apt-get install xvfb (Debian/Ubuntu) "
                "or yum install xorg-x11-server-Xvfb (RHEL/CentOS)"
            )

        # Build Xvfb command
        cmd = [
            'Xvfb',
            self.display,
            '-screen', '0', f'{self.width}x{self.height}x{self.depth}',
            '-ac',  # Disable access control (allow all connections)
            '-nolisten', 'tcp'  # Don't listen on TCP for security
        ]

        logger.info(f"Starting Xvfb: {' '.join(cmd)}")

        try:
            # Start Xvfb subprocess
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for Xvfb to initialize
            await asyncio.sleep(1)

            # Verify Xvfb is still running
            if self.process.poll() is not None:
                # Process already terminated, read stderr for error details
                stderr = await self.process.stderr.read()
                error_msg = stderr.decode('utf-8', errors='replace')
                raise RuntimeError(
                    f"Xvfb failed to start. Exit code: {self.process.returncode}\n"
                    f"Error: {error_msg}"
                )

            # Set DISPLAY environment variable
            os.environ['DISPLAY'] = self.display

            logger.info(
                f"Xvfb started successfully on {self.display} "
                f"({self.width}x{self.height}x{self.depth})"
            )

            return self.display

        except FileNotFoundError:
            raise RuntimeError(
                "Failed to execute Xvfb. Ensure it's installed and in PATH."
            )
        except Exception as e:
            # Cleanup on failure
            if self.process and self.process.returncode is None:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3)
            raise RuntimeError(f"Failed to start Xvfb: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop Xvfb process and cleanup display environment.

        Args:
            exc_type: Exception type if context exited with exception
            exc_val: Exception value if context exited with exception
            exc_tb: Exception traceback if context exited with exception

        Returns:
            False to propagate exceptions (don't suppress)
        """
        logger.info("Cleaning up Xvfb process")

        if self.process:
            try:
                # Terminate gracefully
                self.process.terminate()

                try:
                    # Wait for graceful shutdown
                    await asyncio.wait_for(self.process.wait(), timeout=3)
                    logger.info("Xvfb terminated gracefully")
                except asyncio.TimeoutError:
                    # Force kill if still running
                    logger.warning("Xvfb did not terminate gracefully, killing process")
                    self.process.kill()
                    await self.process.wait()
                    logger.info("Xvfb killed")

            except Exception as e:
                logger.error(f"Error during Xvfb cleanup: {e}")

        # Unset DISPLAY environment variable
        os.environ.pop('DISPLAY', None)

        logger.info("Xvfb cleanup complete")

        # Don't suppress exceptions
        return False

    def get_display_info(self) -> dict:
        """Get current display configuration information.

        Returns:
            Dictionary with display, resolution, and depth information
        """
        return {
            'display': self.display,
            'resolution': f'{self.width}x{self.height}',
            'width': self.width,
            'height': self.height,
            'depth': self.depth,
            'running': self.process is not None and self.process.returncode is None
        }
