"""FFmpeg encoder for video streaming to Cast devices.

Manages FFmpeg encoding process that captures video from Xvfb virtual display
and encodes to H.264 with configurable quality settings. Supports dual output modes:
- HLS: Buffered streaming with .m3u8 playlist and .ts segments
- fMP4: Low-latency fragmented MP4 streaming
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .network import get_host_ip
from .quality import QualityConfig


logger = logging.getLogger(__name__)


class FFmpegEncoder:
    """Manages FFmpeg encoding process for video streaming.

    Captures video from Xvfb virtual display and encodes to H.264 with
    configurable quality settings. Supports two output modes:
    - HLS: Buffered streaming with playlist (.m3u8) and segments (.ts)
    - fMP4: Low-latency fragmented MP4 for real-time content

    Uses async context manager for proper process lifecycle management.

    Usage:
        config = get_quality_config('1080p')
        async with FFmpegEncoder(config, display=':99', mode='hls') as stream_url:
            # Encoding runs until context exit
            await asyncio.sleep(30)  # Stream for 30 seconds
    """

    def __init__(
        self,
        quality: QualityConfig,
        display: str = ':99',
        output_dir: str = '/tmp/streams',
        port: int = 8080,
        mode: Literal['hls', 'fmp4'] = 'hls'
    ):
        """Initialize FFmpeg encoder.

        Args:
            quality: Quality configuration for encoding
            display: X11 display number to capture from
            output_dir: Directory for output stream files
            port: Streaming server port for URL construction
            mode: Output format - 'hls' for buffered streaming, 'fmp4' for low-latency
        """
        self.quality = quality
        self.display = display
        self.output_dir = output_dir
        self.port = port
        self.mode = mode
        self.process = None
        self.output_path = None

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def build_ffmpeg_args(self, output_file: str) -> list[str]:
        """Construct FFmpeg argument list based on quality config and output mode.

        Args:
            output_file: Full path to output file

        Returns:
            List of FFmpeg arguments (excludes 'ffmpeg' command itself)
        """
        width, height = self.quality.resolution
        bitrate = self.quality.bitrate
        framerate = self.quality.framerate
        preset = self.quality.preset

        # Base arguments for x11grab input (video source)
        args = [
            # Video input configuration
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

            # H.264 profile/level for Cast compatibility
            '-profile:v', 'high',
            '-level:v', '4.1',
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

        # Output format based on mode
        if self.mode == 'hls':
            # HLS output: buffered streaming with playlist and segments
            args.extend([
                '-f', 'hls',
                '-hls_time', '2',  # 2-second segments
                '-hls_list_size', '3',  # Keep 3 segments in playlist
                '-hls_flags', 'delete_segments',  # Auto-cleanup old segments
                output_file,
            ])
        else:
            # fMP4 output: low-latency fragmented MP4
            args.extend([
                '-f', 'mp4',
                '-movflags', 'frag_keyframe+empty_moov+default_base_moof',
                output_file,
            ])

        return args

    async def __aenter__(self) -> str:
        """Start FFmpeg encoding process.

        Returns:
            HTTP URL for the stream file (m3u8 for HLS, mp4 for fMP4)

        Raises:
            FileNotFoundError: If ffmpeg is not in PATH
            RuntimeError: If output file not created after startup
        """
        # Check for ffmpeg availability
        if not shutil.which('ffmpeg'):
            raise FileNotFoundError(
                "ffmpeg not found in PATH. Install FFmpeg to use video encoding."
            )

        # Generate unique output filename based on mode
        stream_id = uuid4().hex
        if self.mode == 'hls':
            output_filename = f"stream_{stream_id}.m3u8"
        else:
            output_filename = f"stream_{stream_id}.mp4"
        self.output_path = os.path.join(self.output_dir, output_filename)

        # Build FFmpeg arguments
        args = self.build_ffmpeg_args(self.output_path)

        logger.info(
            f"Starting FFmpeg encoder: {self.quality.resolution[0]}x{self.quality.resolution[1]} "
            f"@ {self.quality.bitrate}kbps, preset={self.quality.preset}, "
            f"latency_mode={self.quality.latency_mode}, mode={self.mode}"
        )

        # Start FFmpeg subprocess
        self.process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        logger.info(f"FFmpeg process started (PID: {self.process.pid})")

        # Wait for output file to be created
        # HLS needs segment time (2s) + overhead, fMP4 needs less time
        max_wait = 5 if self.mode == 'hls' else 3
        file_type = "HLS playlist" if self.mode == 'hls' else "fMP4 stream"

        for i in range(max_wait):
            await asyncio.sleep(1)
            if os.path.exists(self.output_path):
                break
            # Check if process died
            if self.process.returncode is not None:
                stderr = await self.process.stderr.read()
                error_msg = stderr.decode('utf-8', errors='replace')
                raise RuntimeError(
                    f"FFmpeg exited with code {self.process.returncode}. "
                    f"Error: {error_msg}"
                )
            logger.debug(f"Waiting for {file_type}... ({i+1}/{max_wait}s)")

        # Verify output file exists
        if not os.path.exists(self.output_path):
            # FFmpeg still running but no output - check stderr
            try:
                stderr = await asyncio.wait_for(
                    self.process.stderr.read(2048),
                    timeout=1.0
                )
                error_msg = stderr.decode('utf-8', errors='replace')
            except asyncio.TimeoutError:
                error_msg = "No error output available (process still running)"

            raise RuntimeError(
                f"FFmpeg failed to create {file_type} at {self.output_path} after {max_wait}s. "
                f"Stderr: {error_msg}"
            )

        logger.info(f"{file_type} created: {self.output_path}")

        # Return HTTP URL accessible from Cast device on local network
        host_ip = get_host_ip()
        return f"http://{host_ip}:{self.port}/{output_filename}"

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
                # Remove main output file (m3u8 or mp4)
                os.remove(self.output_path)

                # For HLS mode, also remove segment files (*.ts files with same base name)
                if self.mode == 'hls':
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
