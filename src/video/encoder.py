"""FFmpeg encoder for video streaming to Cast devices.

Manages FFmpeg encoding process that captures video from Xvfb virtual display
and encodes to H.264 with configurable quality settings using HLS output format.
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from uuid import uuid4

from .quality import QualityConfig


logger = logging.getLogger(__name__)


class FFmpegEncoder:
    """Manages FFmpeg encoding process for video streaming.

    Captures video from Xvfb virtual display and encodes to H.264 with
    configurable quality settings. Uses async context manager for proper
    process lifecycle management.

    Usage:
        config = get_quality_config('1080p')
        async with FFmpegEncoder(config, display=':99') as stream_url:
            # Encoding runs until context exit
            await asyncio.sleep(30)  # Stream for 30 seconds
    """

    def __init__(
        self,
        quality: QualityConfig,
        display: str = ':99',
        output_dir: str = '/tmp/streams'
    ):
        """Initialize FFmpeg encoder.

        Args:
            quality: Quality configuration for encoding
            display: X11 display number to capture from
            output_dir: Directory for output stream files
        """
        self.quality = quality
        self.display = display
        self.output_dir = output_dir
        self.process = None
        self.output_path = None

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def build_ffmpeg_args(self, output_file: str) -> list[str]:
        """Construct FFmpeg argument list based on quality config.

        Args:
            output_file: Full path to output file

        Returns:
            List of FFmpeg arguments (excludes 'ffmpeg' command itself)
        """
        width, height = self.quality.resolution
        bitrate = self.quality.bitrate
        framerate = self.quality.framerate
        preset = self.quality.preset

        # Base arguments for x11grab input
        args = [
            # Input configuration
            '-f', 'x11grab',
            '-video_size', f'{width}x{height}',
            '-framerate', str(framerate),
            '-i', self.display,

            # Video codec and encoding settings
            '-c:v', 'libx264',
            '-preset', preset,
            '-b:v', f'{bitrate}k',
            '-maxrate', f'{bitrate}k',
            '-bufsize', f'{bitrate * 2}k',
        ]

        # Latency-specific tuning
        if self.quality.latency_mode == 'low':
            # Low-latency mode: optimize for minimal delay
            args.extend([
                '-tune', 'zerolatency',
                '-bf', '0',  # No B-frames
                '-refs', '1',  # Single reference frame
                '-g', str(framerate),  # GOP size = framerate
                '-max_delay', '0',  # No muxing delay
            ])
        else:
            # Normal mode: balanced quality and latency
            args.extend([
                '-g', str(framerate * 2),  # GOP size = 2 seconds
                '-bf', '2',  # 2 B-frames for better compression
                '-refs', '3',  # 3 reference frames
            ])

        # HLS output format for streaming
        args.extend([
            '-f', 'hls',
            '-hls_time', '2',  # 2-second segments
            '-hls_list_size', '3',  # Keep 3 segments in playlist
            '-hls_flags', 'delete_segments',  # Auto-cleanup old segments
            output_file,
        ])

        return args

    async def __aenter__(self) -> str:
        """Start FFmpeg encoding process.

        Returns:
            HTTP URL for the HLS playlist (m3u8 file)

        Raises:
            FileNotFoundError: If ffmpeg is not in PATH
            RuntimeError: If HLS playlist not created after startup
        """
        # Check for ffmpeg availability
        if not shutil.which('ffmpeg'):
            raise FileNotFoundError(
                "ffmpeg not found in PATH. Install FFmpeg to use video encoding."
            )

        # Generate unique output filename
        stream_id = uuid4().hex
        output_filename = f"stream_{stream_id}.m3u8"
        self.output_path = os.path.join(self.output_dir, output_filename)

        # Build FFmpeg arguments
        args = self.build_ffmpeg_args(self.output_path)

        logger.info(
            f"Starting FFmpeg encoder: {self.quality.resolution[0]}x{self.quality.resolution[1]} "
            f"@ {self.quality.bitrate}kbps, preset={self.quality.preset}, "
            f"latency_mode={self.quality.latency_mode}"
        )

        # Start FFmpeg subprocess
        self.process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        logger.info(f"FFmpeg process started (PID: {self.process.pid})")

        # Wait for HLS playlist to be created
        await asyncio.sleep(2)

        # Verify output file exists
        if not os.path.exists(self.output_path):
            # Try to get error output
            try:
                stderr = await asyncio.wait_for(
                    self.process.stderr.read(1024),
                    timeout=1.0
                )
                error_msg = stderr.decode('utf-8', errors='replace')
            except asyncio.TimeoutError:
                error_msg = "No error output available"

            raise RuntimeError(
                f"FFmpeg failed to create HLS playlist at {self.output_path}. "
                f"Error: {error_msg}"
            )

        logger.info(f"HLS playlist created: {self.output_path}")

        # Return HTTP URL (will be served by HTTP server in Phase 4)
        # For now, return the file path
        return f"http://localhost:8080/{output_filename}"

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop FFmpeg process and clean up output files.

        Args:
            exc_type: Exception type if context exited due to exception
            exc_val: Exception value if context exited due to exception
            exc_tb: Exception traceback if context exited due to exception
        """
        if self.process is None:
            return

        logger.info(f"Stopping FFmpeg process (PID: {self.process.pid})")

        # Terminate gracefully
        self.process.terminate()

        try:
            # Wait up to 5 seconds for graceful shutdown
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
            logger.info("FFmpeg process terminated gracefully")
        except asyncio.TimeoutError:
            # Force kill if still running
            logger.warning("FFmpeg did not terminate gracefully, forcing kill")
            self.process.kill()
            await self.process.wait()
            logger.info("FFmpeg process killed")

        # Clean up output files
        if self.output_path and os.path.exists(self.output_path):
            try:
                # Remove playlist file
                os.remove(self.output_path)

                # Remove segment files (*.ts files with same base name)
                output_dir = os.path.dirname(self.output_path)
                base_name = os.path.splitext(os.path.basename(self.output_path))[0]
                for file in os.listdir(output_dir):
                    if file.startswith(base_name) and file.endswith('.ts'):
                        segment_path = os.path.join(output_dir, file)
                        os.remove(segment_path)

                logger.info(f"Cleaned up output files: {self.output_path}")
            except OSError as e:
                logger.warning(f"Failed to clean up output files: {e}")

        logger.info("FFmpeg encoder cleanup complete")

        # Don't suppress exceptions
        return False
