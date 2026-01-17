"""HTTP streaming server for serving video streams to Cast devices.

This module provides an async HTTP server using aiohttp that serves HLS
playlists and video segments with proper CORS headers for Cast device access.
"""

import os
from pathlib import Path
from typing import Optional

from aiohttp import web

import structlog

from .network import get_host_ip

logger = structlog.get_logger()

# Content-Type mappings for video streaming files
CONTENT_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".ts": "video/MP2T",
    ".mp4": "video/mp4",
}


class StreamingServer:
    """HTTP server for serving video streams to Cast devices.

    Serves static files from a configured directory with proper CORS headers
    to allow Cast devices to access HLS playlists and video segments.

    Usage:
        server = StreamingServer(port=8080, stream_dir="/tmp/streams")
        await server.start()
        # Server is running...
        url = server.get_stream_url("stream.m3u8")
        # Cast device can access: http://192.168.1.100:8080/stream.m3u8
        await server.stop()
    """

    def __init__(self, port: int = 8080, stream_dir: str = "/tmp/streams"):
        """Initialize the streaming server.

        Args:
            port: HTTP port to listen on (default: 8080)
            stream_dir: Directory containing stream files to serve
        """
        self.port = port
        self.stream_dir = Path(stream_dir)
        self.host_ip = get_host_ip()
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

        # Ensure stream directory exists
        self.stream_dir.mkdir(parents=True, exist_ok=True)

    def _add_cors_headers(self, response: web.Response) -> web.Response:
        """Add CORS headers to a response.

        Args:
            response: The response to add headers to

        Returns:
            The response with CORS headers added
        """
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    def _get_content_type(self, filename: str) -> str:
        """Get the Content-Type for a file based on extension.

        Args:
            filename: Name of the file

        Returns:
            Appropriate Content-Type string
        """
        ext = Path(filename).suffix.lower()
        return CONTENT_TYPES.get(ext, "application/octet-stream")

    async def _handle_options(self, request: web.Request) -> web.Response:
        """Handle CORS preflight OPTIONS requests.

        Args:
            request: The incoming OPTIONS request

        Returns:
            Empty response with CORS headers
        """
        logger.debug("cors_preflight", path=request.path)
        response = web.Response(status=204)
        return self._add_cors_headers(response)

    async def _handle_file(self, request: web.Request) -> web.Response:
        """Serve a file from the stream directory.

        Args:
            request: The incoming file request

        Returns:
            File response with appropriate Content-Type and CORS headers
        """
        # Get requested filename (strip leading slash)
        filename = request.match_info.get("filename", "")
        filepath = self.stream_dir / filename

        logger.debug("file_request", filename=filename, filepath=str(filepath))

        # Security: prevent directory traversal
        try:
            filepath = filepath.resolve()
            if not str(filepath).startswith(str(self.stream_dir.resolve())):
                logger.warning("directory_traversal_attempt", filename=filename)
                return web.Response(status=403, text="Forbidden")
        except (ValueError, RuntimeError):
            return web.Response(status=400, text="Invalid path")

        # Check if file exists
        if not filepath.is_file():
            logger.debug("file_not_found", filepath=str(filepath))
            return web.Response(status=404, text="Not Found")

        # Read and serve the file
        try:
            content = filepath.read_bytes()
            content_type = self._get_content_type(filename)

            response = web.Response(
                body=content,
                content_type=content_type,
            )
            return self._add_cors_headers(response)
        except OSError as e:
            logger.error("file_read_error", filepath=str(filepath), error=str(e))
            return web.Response(status=500, text="Internal Server Error")

    async def start(self) -> None:
        """Start the HTTP server.

        The server will listen on all interfaces (0.0.0.0) on the configured
        port. Stream files can be accessed at http://{host_ip}:{port}/{filename}.

        Raises:
            RuntimeError: If the server is already running
        """
        if self._runner is not None:
            raise RuntimeError("Server is already running")

        # Create aiohttp application
        self._app = web.Application()

        # Route: OPTIONS for any path (CORS preflight)
        self._app.router.add_route("OPTIONS", "/{filename:.*}", self._handle_options)

        # Route: GET for stream files
        self._app.router.add_get("/{filename:.*}", self._handle_file)

        # Start the server
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        # Listen on all interfaces
        self._site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await self._site.start()

        logger.info(
            "streaming_server_started",
            port=self.port,
            host_ip=self.host_ip,
            stream_dir=str(self.stream_dir),
        )

    async def stop(self) -> None:
        """Stop the HTTP server gracefully.

        This method is idempotent - calling it multiple times is safe.
        """
        if self._runner is not None:
            logger.info("streaming_server_stopping", port=self.port)
            await self._runner.cleanup()
            self._runner = None
            self._site = None
            self._app = None
            logger.info("streaming_server_stopped")

    def get_stream_url(self, filename: str) -> str:
        """Get the full HTTP URL for a stream file.

        This URL is accessible from Cast devices on the local network.

        Args:
            filename: Name of the stream file (e.g., "stream.m3u8")

        Returns:
            Full HTTP URL (e.g., "http://192.168.1.100:8080/stream.m3u8")
        """
        return f"http://{self.host_ip}:{self.port}/{filename}"
