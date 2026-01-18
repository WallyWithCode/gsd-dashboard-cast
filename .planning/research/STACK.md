# Stack Research: v2.0 Stability and Hardware Acceleration

**Domain:** Cast streaming service enhancement
**Researched:** 2026-01-18
**Confidence:** MEDIUM-HIGH

## Summary

v2.0 requires four stack enhancements to the existing validated system:
1. Intel QuickSync hardware acceleration via h264_qsv encoder
2. pychromecast status listeners for detecting device-initiated cast stops
3. HLS configuration tuning to eliminate 6-second freeze
4. Process monitoring with psutil for FFmpeg lifecycle management

All required components are available and well-documented, but specific Proxmox GPU passthrough configuration and HLS tuning will require testing to optimize.

---

## Core Technologies (Existing - Validated in v1.0/v1.1)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.11 | Runtime | ✓ Validated |
| FastAPI | latest | Webhook API | ✓ Validated |
| aiohttp | latest | HTTP streaming server | ✓ Validated |
| Playwright | latest | Browser automation | ✓ Validated |
| pychromecast | 14.0.9 | Cast protocol | ✓ Validated |
| FFmpeg | latest | Video encoding | ✓ Validated (software encoding) |
| Xvfb | latest | Virtual display | ✓ Validated |
| Docker | latest | Containerization | ✓ Validated |

---

## New Components for v2.0

### Hardware Acceleration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FFmpeg with QSV | 7.0+ | Intel QuickSync hardware encoding | OneVPL support for Gen 12+ (11th gen Core and newer), dramatically reduced CPU usage compared to software encoding |
| Intel Media Driver | latest | VA-API implementation for QuickSync | Required for /dev/dri access on modern Intel GPUs (Broadwell and newer) |
| libva | 2.22.0+ | Video Acceleration API | Foundation for hardware acceleration on Linux |

### Process Monitoring

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| psutil | 7.2.1+ | Process lifecycle monitoring | Track FFmpeg subprocess, detect orphans, ensure cleanup on cast stop |

### pychromecast Enhancement

| Component | Current Version | New Usage | Purpose |
|-----------|----------------|-----------|---------|
| pychromecast | 14.0.9 | MediaStatusListener callbacks | Detect IDLE player_state when user stops cast from Android TV device |

---

## Installation

### Core (Existing)
```bash
# Already in requirements.txt
pip install fastapi aiohttp playwright pychromecast
playwright install chromium
```

### New Dependencies for v2.0
```bash
# Process monitoring
pip install psutil>=7.2.1

# FFmpeg with QSV support (Docker build stage)
# Install Intel Media Driver and VA-API libraries
apt-get install -y \
    intel-media-va-driver \
    libva-drm2 \
    libva2 \
    vainfo

# Verify hardware acceleration availability
vainfo  # Should show /dev/dri/renderD128 with supported codecs
```

### Docker Configuration
```dockerfile
# Add to Dockerfile for GPU passthrough
# Map /dev/dri device for QuickSync access
docker run -d \
    --device=/dev/dri:/dev/dri \
    --group-add video \
    --group-add render \
    -v /dev/dri:/dev/dri \
    dashboard-cast
```

---

## FFmpeg QuickSync (h264_qsv) Configuration

### Recommended Encoder Settings

**Use h264_qsv encoder instead of libx264:**

```python
# Current software encoding (v1.1)
'-c:v', 'libx264',
'-preset', 'medium',
'-b:v', f'{bitrate}k',

# New hardware encoding (v2.0)
'-init_hw_device', 'vaapi=va:/dev/dri/renderD128,driver=iHD',
'-init_hw_device', 'qsv=qs@va',
'-hwaccel', 'qsv',
'-c:v', 'h264_qsv',
'-preset', 'medium',  # veryfast, faster, fast, medium, slow, slower, veryslow
'-global_quality', '23',  # ICQ mode: 18-25 range (lower = higher quality)
'-look_ahead', '1',  # Enable look-ahead for better quality
'-look_ahead_depth', '30',  # Analyze 30 frames ahead
```

### Quality Parameters

| Parameter | Purpose | Recommended Value | Notes |
|-----------|---------|-------------------|-------|
| `-global_quality` | ICQ quality (similar to CRF) | 21-25 | Lower = higher quality. 21 for high quality, 25 for balanced |
| `-preset` | Encoding speed preset | medium or slow | Minimal quality impact, use medium for 1080p30 |
| `-look_ahead` | Enable lookahead algorithm | 1 | Improves quality with minimal performance cost |
| `-look_ahead_depth` | Frames to analyze ahead | 30-60 | Higher = better quality, 30 is good default |
| `-profile:v` | H.264 profile | high | Match existing Cast compatibility |
| `-level:v` | H.264 level | 4.1 or 4.2 | 4.1 for universal compatibility, 4.2 for higher bitrates |
| `-adaptive_b` | Adaptive B-frames | 1 | QSV-specific quality enhancement |
| `-rdo` | Rate distortion optimization | 1 | Enable for better compression |

### Bitrate Control

**Constant Quality (ICQ - Recommended):**
```python
'-global_quality', '23',  # Target quality level
'-maxrate', f'{bitrate}k',  # Cap maximum bitrate
'-bufsize', f'{bitrate * 2}k',  # VBV buffer size
```

**Constant Bitrate (CBR - For bandwidth-constrained networks):**
```python
'-b:v', f'{bitrate}k',
'-maxrate', f'{bitrate}k',
'-bufsize', f'{bitrate}k',
```

### Hardware Detection

**Verify QuickSync availability at runtime:**
```python
import subprocess

def check_qsv_available():
    """Check if Intel QuickSync is available on /dev/dri/renderD128."""
    try:
        # Check for render device
        if not os.path.exists('/dev/dri/renderD128'):
            return False

        # Verify FFmpeg can initialize QSV
        result = subprocess.run(
            ['ffmpeg', '-v', 'verbose',
             '-init_hw_device', 'vaapi=va:/dev/dri/renderD128',
             '-init_hw_device', 'qsv=hw@va'],
            capture_output=True,
            text=True,
            timeout=5
        )

        return 'libva info: VA-API version' in result.stderr
    except Exception:
        return False
```

---

## HLS Configuration Fix for 6-Second Freeze

### Problem Analysis

Current configuration (v1.1):
```python
'-hls_time', '2',  # 2-second segments
'-hls_list_size', '10',  # Keep 10 segments (20s buffer)
'-hls_flags', 'delete_segments+append_list',
```

**Issue:** 6-second freeze suggests buffering starvation or playlist update latency.

### Recommended HLS Parameters

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `hls_time` | 2 | 1-2 | Keep 2s for stability, or try 1s for lower latency |
| `hls_list_size` | 10 | 20-30 | Increase playlist window to 20-60s for better buffering |
| `hls_flags` | delete_segments+append_list | delete_segments+append_list+omit_endlist | Add omit_endlist for continuous streams |
| `hls_segment_type` | (default mpegts) | mpegts or fmp4 | mpegts proven, fmp4 alternative for low-latency |
| NEW: `hls_playlist_type` | (none) | event | Prevents premature stream end detection |

### Updated Configuration

```python
# For continuous streaming without freeze
if self.mode == 'hls':
    args.extend([
        '-f', 'hls',
        '-hls_time', '2',  # 2-second segments (proven stable)
        '-hls_list_size', '20',  # 40-second buffer window (increased from 10)
        '-hls_flags', 'delete_segments+append_list+omit_endlist',  # Added omit_endlist
        '-hls_playlist_type', 'event',  # Prevent premature end-of-stream
        '-hls_segment_type', 'mpegts',  # Explicit segment type
        output_file,
    ])
```

### GOP Alignment (Critical)

**Must align keyframe interval with segment duration:**

```python
# For hls_time=2, ensure GOP = 2 * framerate
if self.mode == 'hls':
    args.extend([
        '-g', str(framerate * 2),  # Keyframe every 2 seconds
        '-keyint_min', str(framerate * 2),  # Minimum keyframe interval
        '-force_key_frames', f'expr:gte(t,n_forced*2)',  # Force keyframes every 2s
    ])
```

### Alternative: Low-Latency HLS

For sub-2-second latency (experimental):
```python
'-hls_time', '1',  # 1-second segments
'-hls_list_size', '30',  # 30-second window
'-hls_flags', 'delete_segments+append_list+omit_endlist+program_date_time',
'-g', str(framerate),  # Keyframe every 1 second
```

**Tradeoff:** More HTTP requests, potential buffering on slower networks.

---

## pychromecast Status Listener for Device-Initiated Stop Detection

### MediaStatusListener Implementation

**Use MediaStatusListener to detect when user stops cast from Android TV:**

```python
from pychromecast.controllers.media import MediaStatusListener, MEDIA_PLAYER_STATE_IDLE

class CastStopDetector(MediaStatusListener):
    """Detects when cast session stops from device (not API)."""

    def __init__(self, on_stop_callback):
        """
        Args:
            on_stop_callback: Async function to call when cast stops
        """
        self.on_stop_callback = on_stop_callback
        self._last_session_id = None

    def new_media_status(self, status):
        """Called when media status changes.

        Args:
            status: MediaStatus object with player_state, media_session_id, idle_reason
        """
        # Detect transition to IDLE state (cast stopped)
        if status.player_state == MEDIA_PLAYER_STATE_IDLE:
            # Check if session actually ended (not just paused)
            if self._last_session_id and status.media_session_id is None:
                logger.info(f"Cast stopped from device (idle_reason: {status.idle_reason})")
                # Trigger cleanup asynchronously
                asyncio.create_task(self.on_stop_callback())

        # Track active session ID
        self._last_session_id = status.media_session_id

    def load_media_failed(self, queue_item_id, error_code):
        """Called when media load fails."""
        logger.warning(f"Media load failed: queue_item_id={queue_item_id}, error={error_code}")
```

### Integration with CastSessionManager

```python
# In CastSessionManager.__aenter__
async def __aenter__(self):
    # ... existing setup ...

    # Register status listener to detect device-initiated stops
    self._stop_detector = CastStopDetector(on_stop_callback=self._handle_device_stop)
    self.device.media_controller.register_status_listener(self._stop_detector)

    return self

async def _handle_device_stop(self):
    """Handle cast stop initiated from device (not API)."""
    logger.info("Device-initiated cast stop detected, cleaning up FFmpeg")
    # Trigger FFmpeg cleanup and session termination
    await self.stop_cast()
```

### Player States to Monitor

| State | Value | Meaning | Action |
|-------|-------|---------|--------|
| IDLE | "IDLE" | No media playing, session may be inactive | Check media_session_id - if None, session ended |
| PLAYING | "PLAYING" | Media actively playing | Normal operation |
| PAUSED | "PAUSED" | Media paused | Normal operation, don't cleanup |
| BUFFERING | "BUFFERING" | Loading/buffering media | Normal operation |
| UNKNOWN | "UNKNOWN" | State unknown | Ignore, may be transient |

### Idle Reasons (for logging)

When `player_state == IDLE`, the `idle_reason` field indicates why:
- `FINISHED`: Playback completed naturally
- `CANCELLED`: User stopped playback
- `INTERRUPTED`: Another app took control
- `ERROR`: Playback error occurred

---

## Process Monitoring with psutil

### FFmpeg Process Lifecycle Management

**Use psutil to track FFmpeg subprocess and ensure cleanup:**

```python
import psutil
import asyncio

class FFmpegProcessMonitor:
    """Monitor FFmpeg process lifecycle and ensure cleanup."""

    def __init__(self, process: asyncio.subprocess.Process):
        """
        Args:
            process: asyncio subprocess object for FFmpeg
        """
        self.process = process
        self.psutil_process = psutil.Process(process.pid)

    async def wait_with_monitoring(self, timeout: float = None):
        """Wait for process to complete with status monitoring.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if process terminated cleanly, False if killed/timeout
        """
        try:
            await asyncio.wait_for(self.process.wait(), timeout=timeout)
            return self.process.returncode == 0
        except asyncio.TimeoutError:
            logger.warning(f"FFmpeg process {self.process.pid} timeout after {timeout}s")
            return False

    async def terminate_tree(self, timeout: float = 5.0):
        """Terminate FFmpeg and all child processes gracefully.

        Args:
            timeout: Seconds to wait before force kill

        Returns:
            List of PIDs that were terminated
        """
        terminated_pids = []

        try:
            # Get all child processes (FFmpeg may spawn additional processes)
            children = self.psutil_process.children(recursive=True)
            all_procs = [self.psutil_process] + children

            # Terminate gracefully
            for proc in all_procs:
                try:
                    proc.terminate()
                    terminated_pids.append(proc.pid)
                except psutil.NoSuchProcess:
                    pass

            # Wait for processes to terminate
            gone, alive = psutil.wait_procs(all_procs, timeout=timeout)

            # Force kill any remaining processes
            for proc in alive:
                try:
                    logger.warning(f"Force killing process {proc.pid}")
                    proc.kill()
                    terminated_pids.append(proc.pid)
                except psutil.NoSuchProcess:
                    pass

            logger.info(f"Terminated FFmpeg process tree: {terminated_pids}")
            return terminated_pids

        except psutil.NoSuchProcess:
            logger.debug("FFmpeg process already terminated")
            return terminated_pids

    def is_running(self) -> bool:
        """Check if FFmpeg process is still running."""
        try:
            return self.psutil_process.is_running()
        except psutil.NoSuchProcess:
            return False

    def get_status(self) -> dict:
        """Get current process status and resource usage.

        Returns:
            Dict with status, cpu_percent, memory_mb, children_count
        """
        try:
            return {
                'status': self.psutil_process.status(),
                'cpu_percent': self.psutil_process.cpu_percent(),
                'memory_mb': self.psutil_process.memory_info().rss / 1024 / 1024,
                'children_count': len(self.psutil_process.children(recursive=True))
            }
        except psutil.NoSuchProcess:
            return {'status': 'terminated'}
```

### Integration with FFmpegEncoder

```python
# In FFmpegEncoder.__aenter__
async def __aenter__(self) -> str:
    # ... start FFmpeg subprocess ...
    self.process = await asyncio.create_subprocess_exec(...)

    # Add process monitor
    self.monitor = FFmpegProcessMonitor(self.process)

    return stream_url

# In FFmpegEncoder.__aexit__
async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self.process and self.monitor:
        # Use monitored termination instead of simple terminate()
        await self.monitor.terminate_tree(timeout=5.0)

    # ... rest of cleanup ...
```

### Orphaned Process Detection

**Periodically check for orphaned FFmpeg processes:**

```python
async def cleanup_orphaned_ffmpeg_processes():
    """Find and kill orphaned FFmpeg processes not managed by active sessions."""
    orphaned = []

    for proc in psutil.process_iter(['pid', 'name', 'ppid', 'create_time']):
        try:
            if proc.info['name'] == 'ffmpeg':
                # Check if parent process still exists
                try:
                    parent = psutil.Process(proc.info['ppid'])
                    if not parent.is_running():
                        orphaned.append(proc)
                except psutil.NoSuchProcess:
                    # Parent is dead, this is an orphan
                    orphaned.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Terminate orphaned processes
    for proc in orphaned:
        logger.warning(f"Terminating orphaned FFmpeg process {proc.pid}")
        proc.terminate()

    # Wait and force kill if needed
    gone, alive = psutil.wait_procs(orphaned, timeout=3)
    for proc in alive:
        proc.kill()

    return [proc.pid for proc in orphaned]
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| h264_qsv (QuickSync) | libx264 (software) | No Intel GPU available, or CPU encoding sufficient |
| h264_qsv | h264_vaapi | Older Intel hardware (pre-Broadwell), or non-Intel GPUs |
| psutil | Custom /proc parsing | Never - psutil is cross-platform and maintained |
| HLS hls_time=2 | HLS hls_time=1 | Need sub-2s latency, have reliable network |
| fMP4 mode | HLS mode | Need absolute lowest latency, clients support fMP4 |
| MediaStatusListener | Polling media_controller.status | Never - callbacks are event-driven and efficient |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| h264_vaapi alone | Less efficient than QSV on newer Intel hardware (Gen 12+) | h264_qsv with QSV device initialization |
| `-qsv_device /dev/dri/renderD128` | Causes "Invalid argument" errors, wrong initialization pattern | `-init_hw_device vaapi=va:/dev/dri/renderD128,driver=iHD` then `-init_hw_device qsv=qs@va` |
| `-rc_mode CRF` with QSV | CRF not supported by QSV encoders | `-global_quality` for ICQ mode (similar to CRF) |
| HLS without omit_endlist flag | Cast device may interpret playlist as complete after initial load | Add `omit_endlist` to hls_flags for continuous streams |
| Misaligned GOP and hls_time | Segments can't be cut mid-GOP, causes freeze/delay | Set `-g framerate * hls_time` to align keyframes with segments |
| process.terminate() without timeout | May hang indefinitely if process doesn't respond | Use psutil.wait_procs() with timeout, then kill() |
| Checking process.returncode immediately | Async subprocess may not have status yet | Use psutil.Process.is_running() or psutil.wait_procs() |

---

## Stack Patterns by Variant

### If Intel GPU Available (Recommended for v2.0)
- Use **h264_qsv** encoder with hardware device initialization
- Set `-global_quality 23` for ICQ mode (balanced quality)
- Enable `-look_ahead 1` for quality improvement
- Device passthrough: `--device=/dev/dri:/dev/dri` in Docker
- Verify with `vainfo` before starting encoding

### If No Intel GPU (Fallback)
- Continue using **libx264** software encoder (v1.1 configuration)
- No changes to Docker device configuration
- Consider NVENC (h264_nvenc) if NVIDIA GPU available
- Expect higher CPU usage (60-80% vs 10-15% with QSV)

### If HLS Still Freezes After Configuration
- Try **fMP4 mode** as alternative (already implemented in v1.1)
- Reduce hls_time to 1 second for lower latency
- Increase hls_list_size to 30-40 for larger buffer window
- Add Low-Latency HLS extensions: `-hls_flags program_date_time`
- Test with different Cast device models (may be device-specific)

### If FFmpeg Processes Not Cleaning Up
- Add periodic orphan cleanup task (every 60s)
- Log process status on session start/stop for debugging
- Consider adding process creation timestamp tracking
- Monitor /tmp/streams directory size as proxy metric

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FFmpeg 7.0+ | OneVPL (QSV Gen 12+) | Required for 11th gen Core and newer Intel GPUs |
| FFmpeg 6.x | Intel Media SDK (QSV Gen 5-11) | Works with Broadwell to 10th gen Core |
| pychromecast 14.0.9 | Python 3.11 | Validated in v1.0/v1.1 |
| psutil 7.2.1+ | Python 3.11 | Requires Python 3.6+ |
| h264_qsv | Intel Media Driver 24.x+ | Check with `vainfo` for codec support |
| Docker --device=/dev/dri | Proxmox GPU passthrough | Requires render/video group permissions |
| HLS omit_endlist | Chromecast Gen 3+ | Older devices may not support continuous streams |

### FFmpeg Build Requirements

**Ensure FFmpeg compiled with QSV support:**
```bash
ffmpeg -encoders | grep qsv
# Should show: h264_qsv, hevc_qsv, etc.

ffmpeg -hwaccels
# Should show: qsv, vaapi
```

If not present, rebuild FFmpeg with:
```bash
./configure --enable-libmfx --enable-vaapi
```

---

## Proxmox GPU Passthrough Configuration

### Required Proxmox Host Configuration

**1. Enable IOMMU in GRUB:**
```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"

update-grub
reboot
```

**2. Load Required Modules:**
```bash
# /etc/modules
vfio
vfio_iommu_type1
vfio_pci
vfio_virqfd
```

**3. Verify GPU Available:**
```bash
ls -la /dev/dri/
# Should show: renderD128, card0, etc.

vainfo --display drm --device /dev/dri/renderD128
# Should show: VA-API version, supported codecs (H264, etc.)
```

### VM/Container Configuration

**For LXC containers (unprivileged):**
```bash
# /etc/pve/lxc/<VMID>.conf
lxc.cgroup2.devices.allow: c 226:128 rwm
lxc.mount.entry: /dev/dri/renderD128 dev/dri/renderD128 none bind,optional,create=file
lxc.mount.entry: /dev/dri/card0 dev/dri/card0 none bind,optional,create=file

# Map render group (typically GID 109 or 104)
lxc.idmap: u 0 100000 65536
lxc.idmap: g 0 100000 109
lxc.idmap: g 109 109 1
lxc.idmap: g 110 100110 65426
```

**For VMs:**
- Use PCI passthrough for full GPU access
- Or use mediated device (vGPU) for shared access
- Add to VM configuration: `hostpci0: 00:02.0,rombar=0`

### Docker Integration

**Add to docker-compose.yml:**
```yaml
services:
  dashboard-cast:
    devices:
      - /dev/dri:/dev/dri
    group_add:
      - video
      - render
    volumes:
      - /dev/dri:/dev/dri
```

---

## Sources

### Intel QuickSync / Hardware Acceleration
- [Intel Quick Sync Video - Wikipedia](https://en.wikipedia.org/wiki/Intel_Quick_Sync_Video) — Overview of QSV technology
- [Frigate Discussion #6405](https://github.com/blakeblackshear/frigate/discussions/6405) — VAAPI vs QSV comparison
- [Medium: Hardware-accelerate video transcoding via Quicksync (QSV)](https://medium.com/@yllanos/how-to-hardware-accelerate-video-transcoding-via-quicksync-qsv-while-retaining-hdr-using-linux-afe25780718c) — Docker + QSV setup (HIGH confidence)
- [Jellyfin: HWA Tutorial On Intel GPU](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/intel/) — Official hardware acceleration guide
- [Frigate Discussion #16339](https://github.com/blakeblackshear/frigate/discussions/16339) — Why QuickSync recommended over VAAPI (MEDIUM confidence)
- [Gough's Tech Zone: h264_qsv Codec Round-Up 2023](https://goughlui.com/2023/12/28/video-codec-round-up-2023-part-6-h264_qsv-h-264-intel-quick-sync-video/) — Quality and settings analysis (HIGH confidence)
- [Nelson's Log: hevc_qsv Intel Quick Sync settings](https://nelsonslog.wordpress.com/2022/08/22/ffmpeg-and-hevc_qsv-intel-quick-sync-settings/) — QSV encoder parameters

### Proxmox GPU Passthrough
- [Proxmox Forum: Jellyfin + QSV + unprivileged LXC](https://forum.proxmox.com/threads/guide-jellyfin-remote-network-shares-hw-transcoding-with-intels-qsv-unprivileged-lxc.142639/) — Complete LXC passthrough guide (HIGH confidence)
- [Proxmox Forum: i5-14500t LXC passthrough](https://forum.proxmox.com/threads/i5-14500t-lxc-passthrough-intel-gpu-for-video-transcoding.175890/) — Recent successful setup (2025)
- [Nelson's Log: Intel QuickSync GPU transcoding in Proxmox](https://nelsonslog.wordpress.com/2024/03/03/intel-quicksync-gpu-transcoding-in-proxmox/) — VM/LXC configuration
- [Frigate Discussion #5773](https://github.com/blakeblackshear/frigate/discussions/5773) — Unprivileged LXC with Intel iGPU (11th gen)

### pychromecast Status Listeners
- [pychromecast GitHub: media.py](https://github.com/home-assistant-libs/pychromecast/blob/master/pychromecast/controllers/media.py) — MediaStatusListener source code (HIGH confidence)
- [pychromecast PyPI](https://pypi.org/project/PyChromecast/) — Version 14.0.9 documentation (HIGH confidence)
- [pychromecast Issue #84](https://github.com/home-assistant-libs/pychromecast/issues/84) — "How can I tell when an app stops casting?"
- [pychromecast Issue #168](https://github.com/home-assistant-libs/pychromecast/issues/168) — Listener player_state updates
- [Home Assistant Issue #35780](https://github.com/home-assistant/core/issues/35780) — Exception in media status callback

### HLS Configuration
- [Tebi.io Docs: FFMpeg Reduced Latency HLS](https://docs.tebi.io/streaming/ffmpeg_rl_hls.html) — HLS low-latency configuration (MEDIUM confidence)
- [Martin Riedl: Using FFmpeg as HLS streaming server Part 2](https://www.martin-riedl.de/2018/08/24/using-ffmpeg-as-a-hls-streaming-server-part-2/) — HLS segmentation best practices
- [video.js Issue #6366](https://github.com/videojs/video.js/issues/6366) — HLS + fMP4 lag reduction
- [VideoSDK: HLS Live Streaming Complete Guide 2025](https://www.videosdk.live/developer-hub/hls/hls-live-streaming) — Current HLS practices (MEDIUM confidence)
- [Medium: Rethinking HLS Low-Latency](https://medium.com/@OvenMediaEngine/rethinking-hls-is-it-possible-to-achieve-low-latency-streaming-with-hls-9d00512b3e61) — HLS architecture analysis

### Process Monitoring (psutil)
- [psutil PyPI](https://pypi.org/project/psutil/) — Version 7.2.1 package info (HIGH confidence)
- [psutil GitHub](https://github.com/giampaolo/psutil) — Official repository
- [psutil Documentation](https://psutil.readthedocs.io/) — Complete API reference (HIGH confidence)
- [The Python Code: Process Monitor in Python](https://thepythoncode.com/article/make-process-monitor-python) — Implementation examples (MEDIUM confidence)
- [Medium: System Monitoring with Psutil](https://umeey.medium.com/system-monitoring-made-easy-with-pythons-psutil-library-4b9add95a443) — Usage patterns

---

*Stack research for: v2.0 Stability and Hardware Acceleration*
*Researched: 2026-01-18*
*Confidence: MEDIUM-HIGH (QuickSync and pychromecast HIGH, HLS tuning MEDIUM pending testing)*
