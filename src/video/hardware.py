"""Hardware acceleration detection and configuration for FFmpeg.

Detects Intel QuickSync (h264_qsv) availability at runtime and provides
encoder configuration with graceful fallback to software encoding.
"""

import logging
import subprocess
from typing import TypedDict

logger = logging.getLogger(__name__)


class EncoderConfig(TypedDict):
    """Encoder configuration dictionary."""
    encoder: str  # 'h264_qsv' or 'libx264'
    encoder_args: list[str]  # Encoder-specific arguments


class HardwareAcceleration:
    """Detect and configure hardware acceleration for FFmpeg."""

    def __init__(self):
        self._qsv_available = None

    def is_qsv_available(self) -> bool:
        """Check if Intel QuickSync h264_qsv encoder is available.

        Detection method:
        1. Check ffmpeg -encoders for h264_qsv
        2. Verify /dev/dri/renderD128 accessible via vainfo
        3. Confirm VAEntrypointEncSlice capability exists

        Returns cached result on subsequent calls.

        Returns:
            True if h264_qsv encoder available, False otherwise
        """
        # Return cached result if already checked
        if self._qsv_available is not None:
            return self._qsv_available

        try:
            # Step 1: Check if ffmpeg has h264_qsv encoder
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                errors='replace'
            )

            if result.returncode != 0:
                logger.warning("FFmpeg -encoders command failed, falling back to software encoding")
                self._qsv_available = False
                return False

            if 'h264_qsv' not in result.stdout:
                logger.warning("h264_qsv encoder not found in FFmpeg, falling back to software encoding")
                self._qsv_available = False
                return False

            # Step 2: Verify /dev/dri/renderD128 access via vainfo
            result = subprocess.run(
                ['vainfo', '--display', 'drm', '--device', '/dev/dri/renderD128'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                errors='replace'
            )

            if result.returncode != 0:
                logger.warning(
                    "vainfo command failed (GPU device not accessible), "
                    "falling back to software encoding"
                )
                self._qsv_available = False
                return False

            # Step 3: Check for VAEntrypointEncSlice capability (H.264 encoding support)
            output = result.stdout + result.stderr
            if 'VAEntrypointEncSlice' not in output:
                logger.warning(
                    "VAEntrypointEncSlice not found (GPU doesn't support encoding), "
                    "falling back to software encoding"
                )
                self._qsv_available = False
                return False

            # All checks passed
            logger.info("Intel QuickSync h264_qsv encoder available and accessible")
            self._qsv_available = True
            return True

        except FileNotFoundError as e:
            logger.warning(f"Required command not found ({e.filename}), falling back to software encoding")
            self._qsv_available = False
            return False

        except subprocess.TimeoutExpired:
            logger.warning("Hardware detection timed out, falling back to software encoding")
            self._qsv_available = False
            return False

        except Exception as e:
            logger.warning(f"Unexpected error during hardware detection: {e}, falling back to software encoding")
            self._qsv_available = False
            return False

    def get_encoder_config(self) -> EncoderConfig:
        """Get encoder configuration based on hardware availability.

        Returns:
            EncoderConfig with encoder name and encoder-specific args
        """
        if self.is_qsv_available():
            return {
                'encoder': 'h264_vaapi',  # Use VAAPI instead of QSV for better Linux compatibility
                'encoder_args': [
                    '-qp', '23',      # Constant QP (like CRF for VAAPI)
                ]
            }
        else:
            return {
                'encoder': 'libx264',
                'encoder_args': []  # Use existing preset/bitrate config
            }
