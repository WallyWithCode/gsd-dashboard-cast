# Phase 10: Intel QuickSync Hardware Acceleration - Research

**Researched:** 2026-01-19
**Domain:** FFmpeg hardware video encoding with Intel QuickSync (VAAPI/QSV)
**Confidence:** HIGH

## Summary

Intel QuickSync hardware acceleration uses the h264_qsv encoder in FFmpeg to offload H.264 encoding from CPU to Intel integrated GPU, reducing CPU usage by 75-95% per stream. The current implementation uses libx264 software encoding which cannot achieve real-time performance on 2-vCPU VM.

**Current state:** Dockerfile installs basic FFmpeg package (software encoding only). Docker runs in Proxmox VM without GPU passthrough. Python subprocess launches FFmpeg with libx264 encoder (line 113 in encoder.py).

**Standard approach:** Install FFmpeg with VAAPI/QSV support + Intel media drivers (iHD for Gen 8+). Pass /dev/dri/renderD128 to Docker container with render group permissions. Use h264_qsv encoder with runtime detection and fallback to libx264 if hardware unavailable.

**Primary recommendation:** Replace libx264 with h264_qsv encoder, add Intel media drivers to Dockerfile, configure Docker device passthrough, implement vainfo hardware detection with graceful fallback, and document Proxmox GPU passthrough configuration.

## Standard Stack

The established libraries/tools for Intel QuickSync integration:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FFmpeg | 6.0+ | Video encoder with QSV support | OneVPL support added in 6.0 (Gen 12+ GPUs), h264_qsv encoder |
| intel-media-va-driver-non-free | latest | iHD VAAPI driver | Gen 8+ Intel GPUs (Broadwell/Skylake onwards), best encode quality |
| vainfo | latest | Hardware capability detection | Reports available VA-API encoders/decoders at runtime |
| libva2 | latest | Video Acceleration API | Abstraction layer between FFmpeg and hardware drivers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| i965-va-driver | latest | Legacy VAAPI driver | Gen 5-9 Intel GPUs only (archived Jan 31, 2025, no longer maintained) |
| intel-gpu-tools | latest | Debugging and monitoring | Optional: provides intel_gpu_top for GPU utilization monitoring |
| libmfx1 | latest | Intel Media SDK runtime | Legacy support, superceded by OneVPL for Gen 12+ |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| h264_qsv (QuickSync) | libx264 (software) | Software: 95% CPU, no GPU usage. Hardware: 20% CPU, GPU accelerated |
| h264_qsv | h264_vaapi | h264_vaapi is lower-level API, h264_qsv provides better quality and rate control options |
| h264_qsv | h264_nvenc (NVIDIA) | NVIDIA requires discrete GPU, QuickSync uses integrated GPU (no additional hardware) |

**Installation:**
```bash
# Debian/Ubuntu - Add to Dockerfile
apt-get install -y \
    ffmpeg \
    intel-media-va-driver-non-free \
    vainfo \
    libva2 \
    libva-drm2
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── video/
│   ├── encoder.py           # FFmpeg encoder wrapper (existing)
│   ├── hardware.py          # NEW: Hardware detection module
│   └── quality.py           # Quality configs (existing)
└── health/
    └── check.py             # NEW: Health endpoint with HW status
```

### Pattern 1: Hardware Detection with Graceful Fallback
**What:** Detect QuickSync availability at runtime using vainfo, choose encoder accordingly
**When to use:** Service startup and health checks
**Example:**
```python
# Source: Research synthesis from FileFlows and Frigate implementations
import subprocess
import logging

logger = logging.getLogger(__name__)

class HardwareAcceleration:
    """Detect and configure hardware acceleration for FFmpeg."""

    def __init__(self):
        self._qsv_available = None

    def is_qsv_available(self) -> bool:
        """Check if Intel QuickSync h264_qsv encoder is available.

        Returns:
            True if h264_qsv encoder found, False otherwise
        """
        if self._qsv_available is not None:
            return self._qsv_available

        try:
            # Method 1: Check FFmpeg encoders
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and 'h264_qsv' in result.stdout:
                # Method 2: Verify VAAPI device accessible
                vainfo_result = subprocess.run(
                    ['vainfo', '--display', 'drm', '--device', '/dev/dri/renderD128'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                # Check for H.264 encode capability
                if vainfo_result.returncode == 0 and 'VAEntrypointEncSlice' in vainfo_result.stdout:
                    logger.info("Intel QuickSync h264_qsv encoder available")
                    self._qsv_available = True
                    return True

            logger.warning("Intel QuickSync not available, falling back to software encoding")
            self._qsv_available = False
            return False

        except FileNotFoundError:
            logger.warning("ffmpeg or vainfo not found, falling back to software encoding")
            self._qsv_available = False
            return False
        except subprocess.TimeoutExpired:
            logger.error("Hardware detection timeout, falling back to software encoding")
            self._qsv_available = False
            return False

    def get_encoder_config(self) -> dict:
        """Get encoder configuration based on hardware availability.

        Returns:
            Dict with encoder name and encoder-specific args
        """
        if self.is_qsv_available():
            return {
                'encoder': 'h264_qsv',
                'encoder_args': [
                    '-global_quality', '23',      # ICQ mode: quality target (like CRF)
                    '-look_ahead', '1',           # Enable lookahead rate control
                    '-look_ahead_depth', '40',    # Analyze 40 frames ahead
                ]
            }
        else:
            return {
                'encoder': 'libx264',
                'encoder_args': []  # Uses existing preset/bitrate config
            }
```

### Pattern 2: Docker Device Passthrough Configuration
**What:** Configure Docker Compose to expose /dev/dri with correct permissions
**When to use:** Docker deployment with hardware acceleration
**Example:**
```yaml
# Source: Jellyfin and Immich Docker implementations
version: '3.8'
services:
  cast-service:
    build: .
    devices:
      - /dev/dri:/dev/dri  # Pass entire DRI directory for card0 and renderD128
    group_add:
      - "RENDER_GID"  # Replace with: $(getent group render | cut -d: -f3)
      - "VIDEO_GID"   # Replace with: $(getent group video | cut -d: -f3)
    # ... rest of config
```

### Pattern 3: Encoder-Agnostic FFmpeg Arguments
**What:** Build FFmpeg command that works with both h264_qsv and libx264
**When to use:** FFmpegEncoder.build_ffmpeg_args() modification
**Example:**
```python
# Source: Current encoder.py with QSV integration
def build_ffmpeg_args(self, output_file: str, hw_accel: HardwareAcceleration) -> list[str]:
    """Construct FFmpeg arguments with hardware acceleration support."""

    encoder_config = hw_accel.get_encoder_config()
    encoder = encoder_config['encoder']

    args = [
        # Video input (unchanged)
        '-f', 'x11grab',
        '-video_size', f'{width}x{height}',
        '-framerate', str(framerate),
        '-i', self.display,

        # Audio input (unchanged)
        '-f', 'lavfi',
        '-i', 'anullsrc=r=44100:cl=stereo',

        # Map inputs (unchanged)
        '-map', '0:v',
        '-map', '1:a',

        # Video codec - CHANGED
        '-c:v', encoder,
        '-pix_fmt', 'yuv420p',
    ]

    # Encoder-specific quality settings
    if encoder == 'h264_qsv':
        # QuickSync: Use ICQ mode with global_quality
        args.extend(encoder_config['encoder_args'])
        # Note: bitrate/maxrate NOT used with global_quality (ICQ mode)
    else:
        # libx264: Use existing bitrate/preset settings
        args.extend([
            '-preset', preset,
            '-b:v', f'{bitrate}k',
            '-maxrate', f'{bitrate}k',
            '-bufsize', f'{bitrate * 2}k',
        ])

    # Profile/level (same for both encoders)
    args.extend([
        '-profile:v', 'high',
        '-level:v', '4.1',
    ])

    # ... rest of args (audio, format)

    return args
```

### Anti-Patterns to Avoid
- **Hardcoding encoder:** Don't assume h264_qsv will always be available - detect at runtime
- **Mixing rate control modes:** Don't use `-b:v` (bitrate) with `-global_quality` (ICQ mode) - they conflict
- **Ignoring driver selection:** Don't assume iHD is loaded - older CPUs may load i965, causing encoder failures
- **No health reporting:** Don't hide hardware status - expose via health endpoint for debugging

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hardware capability detection | Custom /proc parsing | vainfo --display drm --device /dev/dri/renderD128 | Reports VAEntrypoint types, driver version, codec profiles - complex parsing already done |
| FFmpeg encoder enumeration | Parse ffmpeg -h full | ffmpeg -encoders \| grep qsv | Standard FFmpeg capability query, handles version differences |
| Render group GID lookup | Hardcode 104 or 109 | getent group render \| cut -d: -f3 | GID varies by distribution/system, getent queries actual system database |
| VAAPI driver selection | Edit /etc/environment | LIBVA_DRIVER_NAME=iHD (env var) | Runtime override without system-wide changes, container-friendly |
| GPU device identification | Assume renderD128 | ls /dev/dri/renderD* for multiple GPUs | Systems with discrete GPU may have renderD129, renderD130, etc. |

**Key insight:** Hardware detection is complex with edge cases (multiple GPUs, driver conflicts, permission issues). Use standard tools (vainfo, ffmpeg -encoders) rather than implementing device probing. These tools handle IOMMU groups, driver loading, and capability enumeration correctly.

## Common Pitfalls

### Pitfall 1: CPU Selection - "F" Suffix Models
**What goes wrong:** Choosing Intel CPUs ending in "F" (e.g., i9-14900KF) which lack integrated graphics
**Why it happens:** "F" models are cheaper but omit iGPU, QuickSync requires integrated GPU
**How to avoid:** Verify CPU model has integrated graphics before assuming QuickSync support
**Warning signs:** vainfo reports "failed to initialize display" or "no VA display"

### Pitfall 2: Permission Denied on /dev/dri/renderD128
**What goes wrong:** Docker container cannot access /dev/dri devices, encoder fails with permission error
**Why it happens:** Container user not in render/video groups, or groups not passed via group_add
**How to avoid:**
- Add user to render group on host: `usermod -aG render <user>`
- Pass group GIDs via docker-compose group_add
- Verify with: `ls -l /dev/dri` (should show render group ownership)
**Warning signs:** FFmpeg error "Cannot load libva.so.2" or "Failed to initialise VAAPI connection"

### Pitfall 3: Driver Conflict - i965 vs iHD
**What goes wrong:** Wrong VAAPI driver loaded for CPU generation, encoding fails or produces artifacts
**Why it happens:** Both drivers may be installed, libva chooses wrong one by default
**How to avoid:**
- Use intel-media-va-driver-non-free (iHD) for Gen 8+ CPUs (Broadwell 2014+)
- Set LIBVA_DRIVER_NAME=iHD explicitly in docker-compose environment
- Verify with: `vainfo | grep "Driver version"` should show "iHD" not "i965"
**Warning signs:** vainfo shows i965 driver on 6th gen+ CPU, or encoding quality is poor

### Pitfall 4: Rate Control Mode Confusion
**What goes wrong:** Using -b:v (bitrate) with -global_quality causes encoder to ignore quality setting
**Why it happens:** h264_qsv supports multiple rate control modes (VBR, CBR, ICQ, CQP), mixing parameters selects wrong mode
**How to avoid:**
- Use `-global_quality` for ICQ mode (quality target, like CRF) - **recommended for streaming**
- Use `-b:v` for VBR/CBR mode (bitrate target)
- Don't use both - encoder silently prefers bitrate mode
**Warning signs:** Stream quality worse than expected despite high global_quality value

### Pitfall 5: Proxmox IOMMU Not Enabled
**What goes wrong:** /dev/dri devices don't exist in VM, GPU passthrough silently fails
**Why it happens:** IOMMU disabled in BIOS or kernel, or vfio-pci modules not loaded
**How to avoid:**
- Enable Intel VT-d in BIOS
- Add `intel_iommu=on iommu=pt` to GRUB_CMDLINE_LINUX_DEFAULT
- Verify with: `dmesg | grep -e DMAR -e IOMMU` should show "IOMMU enabled"
- For LXC: Use device passthrough (Resources > Add > Device Passthrough in Proxmox UI)
**Warning signs:** No /dev/dri directory in container, or vainfo reports no display

### Pitfall 6: Adobe Premiere Pro 2025 GPU Priority (Not Relevant)
**What goes wrong:** H.264 decoding ignores QuickSync after Premiere Pro 25.1 update
**Why it happens:** Adobe changed priority to Nvidia > AMD > Intel for H.264
**How to avoid:** N/A - this is desktop application issue, not server encoding
**Warning signs:** N/A - included for completeness but doesn't affect FFmpeg server encoding

### Pitfall 7: XMP/Memory Speed Issues on Gen 12+ CPUs
**What goes wrong:** Encoding produces laggy output with XMP enabled on Core Ultra 7 265K and similar
**Why it happens:** Memory overclocking may cause QuickSync fixed-function hardware instability
**How to avoid:**
- Test with XMP disabled if experiencing encoding artifacts
- This appears specific to newest Core Ultra series (Lunar Lake, 2024+)
- Unlikely to affect server CPUs in production
**Warning signs:** Video output has stuttering, dropped frames, or visual artifacts despite low CPU usage

## Code Examples

Verified patterns from official sources:

### FFmpeg Command - Software Encoding (Current)
```bash
# Source: Current encoder.py implementation
ffmpeg \
  -f x11grab -video_size 1920x1080 -framerate 30 -i :99 \
  -f lavfi -i anullsrc=r=44100:cl=stereo \
  -map 0:v -map 1:a \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -preset medium \
  -b:v 4000k \
  -maxrate 4000k \
  -bufsize 8000k \
  -profile:v high \
  -level:v 4.1 \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -shortest \
  -f hls -hls_time 2 -hls_list_size 20 \
  output.m3u8
```

### FFmpeg Command - QuickSync Hardware Encoding
```bash
# Source: FFmpeg QuickSync Wiki + Nelson's Blog
ffmpeg \
  -f x11grab -video_size 1920x1080 -framerate 30 -i :99 \
  -f lavfi -i anullsrc=r=44100:cl=stereo \
  -map 0:v -map 1:a \
  -c:v h264_qsv \
  -pix_fmt yuv420p \
  -global_quality 23 \
  -look_ahead 1 \
  -look_ahead_depth 40 \
  -profile:v high \
  -level:v 4.1 \
  -c:a aac -b:a 128k -ar 44100 -ac 2 \
  -shortest \
  -f hls -hls_time 2 -hls_list_size 20 \
  output.m3u8
```

### Hardware Detection - vainfo
```bash
# Source: FFmpeg Hardware/QuickSync Wiki
# Check available encoders/decoders
vainfo --display drm --device /dev/dri/renderD128

# Expected output snippet for QuickSync:
# VAEntrypointVLD = decode
# VAEntrypointEncSlice = encode
# VAProfileH264High : VAEntrypointEncSlice

# Verify FFmpeg recognizes h264_qsv
ffmpeg -encoders | grep qsv

# Expected: h264_qsv (H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration))
```

### Docker Compose - GPU Passthrough
```yaml
# Source: Jellyfin and Immich Docker documentation
version: '3.8'
services:
  cast-service:
    build: .
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - "104"  # render group GID - get with: getent group render | cut -d: -f3
      - "44"   # video group GID - get with: getent group video | cut -d: -f3
    environment:
      - LIBVA_DRIVER_NAME=iHD  # Force iHD driver for Gen 8+ Intel GPUs
    # ... rest of config
```

### Dockerfile - Install Intel Media Drivers
```dockerfile
# Source: Jellyfin HWA documentation + Debian wiki
FROM python:3.11-slim

# Install FFmpeg with Intel QuickSync support
RUN apt-get update && \
    apt-get install -y \
        ffmpeg \
        intel-media-va-driver-non-free \
        vainfo \
        libva2 \
        libva-drm2 && \
    rm -rf /var/lib/apt/lists/*

# Verify installation
RUN ffmpeg -encoders | grep qsv || echo "WARNING: h264_qsv not found"
```

### Health Check - Hardware Status Endpoint
```python
# Source: Frigate health check implementation
from fastapi import APIRouter
from .video.hardware import HardwareAcceleration

router = APIRouter()
hw_accel = HardwareAcceleration()

@router.get("/health")
async def health_check():
    """Health check with hardware acceleration status."""
    return {
        "status": "healthy",
        "hardware_acceleration": {
            "quicksync_available": hw_accel.is_qsv_available(),
            "encoder": hw_accel.get_encoder_config()['encoder']
        }
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Intel Media SDK (libmfx) | OneVPL (libvpl) | FFmpeg 6.0 (2023) | Gen 12+ GPUs require OneVPL, MediaSDK legacy only |
| i965 VAAPI driver | iHD VAAPI driver | Gen 8 Broadwell (2014) | iHD better encode quality, i965 archived Jan 2025 |
| VBR/CBR rate control | ICQ (global_quality) | Always available | ICQ provides quality target like CRF, better for streaming |
| Privileged LXC containers | Unprivileged with device passthrough | Proxmox 7.0 (2021) | Security improvement, requires proper group_add configuration |

**Deprecated/outdated:**
- **i965 driver:** Archived Jan 31, 2025 by Intel, no longer maintained. Use iHD (intel-media-va-driver-non-free) for all modern systems
- **Intel Media SDK:** Use OneVPL for Gen 12+ (11th gen Core, Tiger Lake 2020+). Media SDK still works for older hardware via VPL compatibility layer
- **LIBVA_DRIVER_NAME=i965:** Remove from environment, use iHD or auto-detection

## Open Questions

Things that couldn't be fully resolved:

1. **Specific Proxmox VM GPU passthrough vs LXC container passthrough**
   - What we know: LXC device passthrough simpler (Resources > Add > Device Passthrough in UI), VM passthrough requires IOMMU groups and vfio-pci
   - What's unclear: Current deployment uses Docker in VM - does VM need full PCI passthrough or can /dev/dri be mapped into VM?
   - Recommendation: Test with LXC container first (simpler), document both approaches. Proxmox 8.2.7+ has UI for device passthrough (mode=0666)

2. **Performance targets - 80-90% CPU reduction achievable at 720p/1080p?**
   - What we know: General metrics show QuickSync uses ~20% CPU vs ~95% CPU for software. Phase context mentions 2-vCPU VM insufficient for 720p software encoding
   - What's unclear: Specific reduction percentage for x11grab -> h264_qsv workload (not file transcoding)
   - Recommendation: Measure baseline CPU usage with libx264, verify QuickSync reduction meets requirement. May need to adjust GOP size, lookahead depth for real-time capture

3. **Multiple GPU scenario - integrated + discrete**
   - What we know: Can specify device with `-qsv_device /dev/dri/renderD128` flag
   - What's unclear: Current system GPU configuration unknown - if discrete GPU present, which renderD device is integrated GPU?
   - Recommendation: Add device detection logic that enumerates /dev/dri/renderD* and tests each with vainfo, selects first with H264EncSlice support

4. **Fallback graceful degradation - should encoder switch mid-stream?**
   - What we know: Can detect at startup and choose encoder
   - What's unclear: If hardware becomes unavailable during encoding (driver crash, GPU reset), should system attempt restart with software encoder?
   - Recommendation: Start with startup-only detection. Hardware failures mid-stream are rare, and encoder switching would cause stream interruption anyway. Let FFmpeg process crash and restart with re-detection.

## Sources

### Primary (HIGH confidence)
- [FFmpeg Hardware/QuickSync Wiki](https://trac.ffmpeg.org/wiki/Hardware/QuickSync) - Setup requirements, driver selection, encoder options
- [FFmpeg Codecs Documentation](https://ffmpeg.org/ffmpeg-codecs.html) - h264_qsv encoder parameters
- [Debian HardwareVideoAcceleration Wiki](https://wiki.debian.org/HardwareVideoAcceleration) - VAAPI driver installation, vainfo usage
- [Proxmox PCI Passthrough Wiki](https://pve.proxmox.com/wiki/PCI_Passthrough) - IOMMU configuration, device passthrough

### Secondary (MEDIUM confidence)
- [Jellyfin Intel GPU Hardware Acceleration Guide](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/intel/) - Docker integration, driver selection by generation
- [Intel OneVPL in FFmpeg Article](https://www.intel.com/content/www/us/en/developer/articles/technical/onevpl-in-ffmpeg-for-great-streaming-on-intel-gpus.html) - Gen 12+ support, AV1 capabilities
- [Arch Linux Hardware Video Acceleration Wiki](https://wiki.archlinux.org/title/Hardware_video_acceleration) - Driver compatibility, installation
- [Nelson's Blog - Ubuntu FFmpeg Intel GPU](https://nelsonslog.wordpress.com/2022/08/09/ubuntu-ffmpeg-and-intel-gpu-acceleration/) - Practical h264_qsv setup
- [Nelson's Blog - hevc_qsv Settings](https://nelsonslog.wordpress.com/2022/08/22/ffmpeg-and-hevc_qsv-intel-quick-sync-settings/) - global_quality, lookahead configuration

### Tertiary (LOW confidence - WebSearch only)
- Multiple Proxmox forum threads on iGPU passthrough (2024-2025) - Various LXC/VM approaches
- GitHub discussions: Frigate, Immich, Jellyfin (hardware acceleration implementations)
- Intel Community forum threads on QuickSync issues (artifacts, XMP conflicts)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - FFmpeg with h264_qsv is well-documented, iHD driver standard for Gen 8+
- Architecture: HIGH - Hardware detection pattern proven in Frigate/Jellyfin, fallback strategy standard
- Pitfalls: MEDIUM-HIGH - Permission issues and driver selection well-documented, XMP issue specific to newest CPUs
- Proxmox GPU passthrough: MEDIUM - Multiple approaches documented, need to validate for VM vs LXC specific to current deployment

**Research date:** 2026-01-19
**Valid until:** 60 days (stable technology, driver updates infrequent)

**Key verification needed during planning:**
- Current Proxmox deployment type (VM vs LXC)
- Current CPU generation (determines iHD vs i965)
- Current GPU configuration (integrated only, or integrated + discrete)
- Baseline CPU usage measurement with libx264 at 720p for comparison
