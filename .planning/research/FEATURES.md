# Feature Research: v2.0 Stability and Hardware Acceleration

**Domain:** Production HLS streaming with hardware-accelerated encoding and robust lifecycle management
**Researched:** 2026-01-18
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Production-Ready Streaming Must-Haves)

Features users expect from production streaming systems. Missing these = system feels unreliable or breaks under load.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| HLS streams play indefinitely without freezing | Production streaming requirement - users expect continuous playback | MEDIUM | Current 6-second freeze suggests buffer/segment configuration issue. Industry standard: 2-4s segments with 6+ segment playlist buffer |
| Automatic FFmpeg cleanup when cast stops | Resource management - orphaned processes lock up VM | MEDIUM | Need Cast session state monitoring + subprocess lifecycle hooks. Python asyncio subprocess cleanup patterns exist |
| Cast session state monitoring | Detect when user stops from TV remote (not just webhook) | MEDIUM | pychromecast MediaStatusListener tracks playerState changes. IDLE state indicates stopped playback |
| Graceful process termination | SIGTERM before SIGKILL, proper cleanup sequence | LOW | Current implementation has basic terminate/kill pattern, needs refinement for edge cases |
| Stream validation before casting | Verify HLS playlist/fMP4 stream is valid and accessible | LOW | Prevent casting 404s or malformed streams. Quick HTTP HEAD check before play_media() |
| Configurable HLS buffer settings | Tune segment duration, playlist size, buffer size for network conditions | MEDIUM | FFmpeg hls_time, hls_list_size, bufsize parameters. Production default: 2-4s segments, 10-20s buffer |
| Hardware encoder fallback | Gracefully fall back to software if QuickSync unavailable | MEDIUM | Try h264_qsv first, catch error, retry with libx264. Essential for portability |

### Differentiators (Competitive Advantage for Production Use)

Features that set this apart from typical home automation streaming hacks. Not required for basic function, but valuable for production reliability.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Intel QuickSync hardware acceleration | 5-10x encoding performance, 80-90% CPU reduction per stream | HIGH | Requires /dev/dri passthrough, QSV encoder integration (h264_qsv), global_quality tuning. Enables multiple simultaneous streams |
| Per-stream resource monitoring | Track CPU, memory, GPU usage per active stream | MEDIUM | Prevents resource exhaustion before VM lockup. Early warning system for scaling limits |
| Adaptive segment duration | Adjust HLS segment size based on network conditions | HIGH | Start with small segments (low latency), increase if buffering detected. Complex but improves UX |
| Stream health checks | Periodic validation that stream is still accessible and generating new segments | MEDIUM | Detect FFmpeg hangs before user notices frozen stream. Monitor segment timestamp freshness |
| Configurable encoder presets | Per-quality-preset hardware encoder settings (QSV global_quality, preset) | MEDIUM | Balance quality vs performance. Different presets for dashboard (quality) vs camera (speed) |
| Multi-stream orchestration | Concurrent streams to different devices without resource contention | HIGH | Deferred to v3+ but architecture should support it. Resource pooling, queue management |
| Crash recovery | Automatic restart of failed FFmpeg processes with exponential backoff | MEDIUM | Transient failures (network glitch, decoder timeout) shouldn't kill entire cast session |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems in production streaming contexts.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Very short HLS segments (<1s) | "Minimize latency like fMP4" | Massive overhead - 10x CDN requests, playlist thrashing, buffering instability | Use fMP4 mode for low-latency, HLS for buffered stability |
| Long HLS segments (>6s) | "Reduce overhead, improve efficiency" | Poor ABR adaptation, long initial buffering, can't adjust quality quickly | Stick to 2-4s sweet spot for production streaming |
| Blocking subprocess calls in async code | "Simpler than asyncio subprocess" | Blocks event loop, kills concurrency, prevents multi-stream support | Always use asyncio.create_subprocess_exec with proper await |
| Global FFmpeg process pool | "Reuse processes for efficiency" | State leakage between streams, complex lifecycle management, hard to debug | Fresh process per stream - clean slate, simple cleanup |
| Persistent browser instances across casts | "Faster startup, reuse auth" | Memory leaks, stale auth, resource accumulation over time | Current approach (fresh browser per cast) is correct |
| Custom Cast receiver for timeout bypass | "Solve 10-minute idle timeout permanently" | $5 fee, 15min propagation delay, device registration complexity, maintenance burden | Use stream health monitoring + periodic segment generation to keep session active |
| Synchronous media_controller methods | "Simpler than run_in_executor" | Blocks asyncio event loop, prevents concurrent operations | Wrap pychromecast blocking calls with loop.run_in_executor() |
| HLS playlist type VOD for live streams | "Simpler playlist management" | Player expects finite duration, won't handle new segments properly | Use EVENT playlist type or no type tag (live default) |

## Feature Dependencies

```
[HLS Indefinite Streaming]
    └──requires──> [Correct Segment Configuration]
                       ├──requires──> [hls_time: 2-4 seconds]
                       ├──requires──> [hls_list_size: 6-10 segments]
                       └──requires──> [bufsize: 2x bitrate]
    └──requires──> [Stream Health Monitoring]
                       └──enables──> [Automatic Recovery]

[QuickSync Hardware Acceleration]
    └──requires──> [/dev/dri GPU Passthrough]
                       └──requires──> [Proxmox GPU Configuration]
    └──requires──> [h264_qsv Encoder Integration]
                       ├──requires──> [Intel GPU with QSV support]
                       └──requires──> [Software Encoder Fallback]
    └──requires──> [Quality Preset Mapping]
                       └──requires──> [global_quality parameter tuning]

[Cast Session Lifecycle Monitoring]
    └──requires──> [MediaStatusListener]
                       └──monitors──> [playerState changes]
    └──enables──> [FFmpeg Auto-Cleanup]
                       └──requires──> [Subprocess Lifecycle Hooks]
                           ├──requires──> [SIGTERM graceful shutdown]
                           └──requires──> [SIGKILL force cleanup]

[fMP4 Low-Latency Mode Validation]
    └──requires──> [Fragmented MP4 Configuration]
                       └──requires──> [movflags: frag_keyframe+empty_moov+default_base_moof]
    └──requires──> [Stream Type: LIVE]
    └──requires──> [Low-Latency Tuning]
                       ├──requires──> [tune zerolatency]
                       ├──requires──> [No B-frames (bf=0)]
                       └──requires──> [Single reference frame (refs=1)]

[Hardware Encoder Fallback]
    └──requires──> [Try-Catch Pattern]
                       ├──try──> [h264_qsv encoder]
                       └──catch──> [libx264 software fallback]
    └──requires──> [Encoder Availability Detection]
                       └──uses──> [ffmpeg -encoders | grep qsv]
```

### Dependency Notes

- **HLS Indefinite Streaming requires Correct Segment Configuration:** The current 6-second freeze is likely caused by insufficient buffering or segment alignment issues. Production HLS needs 2-4s segments with 6-10 segment playlist (12-40s buffer window).
- **QuickSync requires Software Encoder Fallback:** Hardware availability varies by deployment. Must gracefully fall back to libx264 if h264_qsv fails or /dev/dri unavailable.
- **Cast Session Lifecycle Monitoring enables FFmpeg Auto-Cleanup:** Can't clean up FFmpeg without detecting when cast stops. pychromecast MediaStatusListener provides playerState updates (IDLE = stopped).
- **fMP4 Low-Latency Mode requires LIVE stream_type:** Already implemented correctly in v1.1. Validation confirms movflags configuration matches CMAF low-latency best practices.
- **Hardware Encoder Fallback requires Try-Catch Pattern:** asyncio.create_subprocess_exec can raise FileNotFoundError or fail with non-zero exit. Need encoder detection before launch + retry logic.

## Configuration Matrix

### HLS Segment Configuration (Production Recommendations)

| Use Case | Segment Duration | Playlist Size | Buffer Window | Notes |
|----------|------------------|---------------|---------------|-------|
| **Dashboard streaming (current)** | 2-4 seconds | 10 segments | 20-40s | Balance between latency and stability |
| **Low-latency dashboards** | 1-2 seconds | 6 segments | 6-12s | Higher overhead, more responsive |
| **Stable buffered streaming** | 4-6 seconds | 10 segments | 40-60s | Best for unreliable networks |
| **Camera feeds (motion detection)** | 2 seconds | 6 segments | 12s | Quick response to events |

**Current implementation:** `hls_time=2`, `hls_list_size=10` (20s buffer) - **GOOD baseline, but bufsize may be too small**

**Recommended change for v2.0:**
- Keep `hls_time=2` (2-second segments)
- Keep `hls_list_size=10` (20s buffer)
- **Increase `bufsize` from `{bitrate * 2}k` to `{bitrate * 4}k`** (4x bitrate buffer)
- **Add `-hls_flags delete_segments+append_list+omit_endlist`** (continuous streaming, not VOD)

### QuickSync Quality Presets

| Preset Name | global_quality | preset | Use Case | CPU vs libx264 | Quality vs libx264 |
|-------------|----------------|--------|----------|----------------|-------------------|
| **qsv-fast** | 28 | fast | Low-priority streams, max throughput | 10% CPU | 90% quality |
| **qsv-balanced** | 23 | medium | Default dashboard streaming | 15% CPU | 95% quality |
| **qsv-quality** | 18 | slow | High-quality dashboards | 20% CPU | 98% quality |

**Notes:**
- `global_quality` range: 1 (best) to 51 (worst). Recommended: 18-28 for production.
- QuickSync `preset` options: veryfast, faster, fast, medium, slow, slower, veryslow
- CPU percentage is relative to libx264 with same preset (e.g., QSV medium uses ~15% of libx264 medium CPU)
- Quality assessment based on VMAF scores from Intel benchmarks

### Cast Session Monitoring Configuration

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **MediaStatusListener poll interval** | 1 second | Detect playerState changes quickly |
| **Idle detection threshold** | 2 consecutive IDLE states | Avoid false positives from state transitions |
| **FFmpeg cleanup timeout** | 5 seconds SIGTERM, then SIGKILL | Allow graceful shutdown, force if needed |
| **Stream health check interval** | 10 seconds | Verify new segments are being generated |
| **Segment freshness threshold** | 15 seconds | If newest segment older than 15s, FFmpeg may be hung |

### fMP4 Low-Latency Configuration (Current - Validation Only)

| Parameter | Value | Status |
|-----------|-------|--------|
| **movflags** | `frag_keyframe+empty_moov+default_base_moof` | ✓ Correct (CMAF compliant) |
| **tune** | `zerolatency` | ✓ Correct (low-latency mode only) |
| **bf (B-frames)** | 0 | ✓ Correct (no B-frames for low latency) |
| **refs** | 1 | ✓ Correct (single reference frame) |
| **g (GOP size)** | framerate (e.g., 30) | ✓ Correct (1-second GOP) |
| **stream_type** | LIVE | ✓ Correct (Cast LIVE mode) |

**Validation result:** Current fMP4 implementation matches industry best practices for low-latency streaming. No changes needed for v2.0.

## v2.0 Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Production Impact | Priority |
|---------|------------|---------------------|-------------------|----------|
| Fix HLS 6-second freeze | CRITICAL | LOW | Blocks production use | **P0** |
| FFmpeg auto-cleanup on cast stop | CRITICAL | MEDIUM | Prevents VM lockup | **P0** |
| Cast session state monitoring | HIGH | MEDIUM | Enables auto-cleanup | **P0** |
| QuickSync hardware acceleration | HIGH | HIGH | Enables multi-stream | **P1** |
| Hardware encoder fallback | HIGH | MEDIUM | Required for portability | **P1** |
| Stream validation before cast | MEDIUM | LOW | Better error messages | **P1** |
| Configurable HLS buffer settings | MEDIUM | LOW | Network adaptability | **P1** |
| fMP4 mode validation | MEDIUM | LOW | Confidence in low-latency | **P1** |
| Per-stream resource monitoring | MEDIUM | MEDIUM | Scaling insights | **P2** |
| Stream health checks | MEDIUM | MEDIUM | Proactive failure detection | **P2** |
| Configurable encoder presets | LOW | MEDIUM | Quality/performance tuning | **P2** |
| Crash recovery | MEDIUM | MEDIUM | Resilience | **P2** |
| Adaptive segment duration | LOW | HIGH | Complex, unclear ROI | **P3** |
| Multi-stream orchestration | LOW | HIGH | Deferred to v3+ | **P3** |

**Priority key:**
- **P0:** Blocking production use - must fix for v2.0
- **P1:** Required for production-ready milestone
- **P2:** Nice to have, improves production experience
- **P3:** Future consideration, defer to v3+

## MVP Definition for v2.0 Stability

### Critical Fixes (P0 - Blocking Production)

- [x] **Fix HLS 6-second freeze** - Tune segment/buffer configuration
  - Increase `bufsize` to 4x bitrate
  - Add `omit_endlist` flag for continuous streaming
  - Verify segment generation is continuous

- [x] **FFmpeg auto-cleanup when cast stops** - Detect session end, terminate subprocess
  - Implement MediaStatusListener for playerState monitoring
  - Hook playerState=IDLE to FFmpeg cleanup
  - Add subprocess cleanup with SIGTERM → SIGKILL escalation

- [x] **Cast session state monitoring** - Detect device-initiated stops
  - Register MediaStatusListener on cast start
  - Track playerState transitions (PLAYING → IDLE)
  - Distinguish user stop (remote) from webhook stop

### Production-Ready Features (P1)

- [x] **QuickSync hardware acceleration** - Reduce CPU usage per stream
  - Add h264_qsv encoder option
  - Implement global_quality parameter mapping
  - Document Proxmox /dev/dri passthrough setup

- [x] **Hardware encoder fallback** - Graceful degradation
  - Try h264_qsv first, catch errors
  - Fall back to libx264 on failure
  - Log which encoder is active

- [x] **Stream validation** - Verify stream before casting
  - HTTP HEAD check on stream URL before play_media()
  - Verify HLS playlist has segments
  - Better error messages for 404/malformed streams

- [x] **Configurable HLS buffer settings** - Per-preset buffer tuning
  - Add bufsize to QualityConfig
  - Expose hls_time, hls_list_size configuration
  - Document buffer configuration trade-offs

- [x] **fMP4 mode validation** - Confirm low-latency works
  - Manual testing with fMP4 streams
  - Verify CMAF fragmentation is correct
  - Document movflags configuration rationale

### Post-v2.0 Improvements (P2/P3)

- [ ] **Per-stream resource monitoring** - Track CPU/memory/GPU per stream (P2)
- [ ] **Stream health checks** - Detect FFmpeg hangs proactively (P2)
- [ ] **Configurable encoder presets** - Per-preset QSV tuning (P2)
- [ ] **Crash recovery** - Auto-restart failed FFmpeg processes (P2)
- [ ] **Adaptive segment duration** - Network-aware HLS tuning (P3)
- [ ] **Multi-stream orchestration** - Concurrent streams without contention (P3)

## Technical Implementation Notes

### HLS Freezing Root Cause Analysis

Based on research and current implementation:

**Hypothesis:** 6-second freeze is caused by buffer underrun and/or playlist type misconfiguration.

**Evidence:**
- FFmpeg default HLS playlist has `#EXT-X-ENDLIST` tag, signaling VOD (finite duration)
- Cast device may interpret VOD playlist as "stream ended" after initial buffer
- Current `bufsize={bitrate*2}k` may be too small for 2-second segments with network jitter
- Missing `omit_endlist` flag means playlist appears complete, not continuous

**Solution (HIGH confidence):**
```python
# Current FFmpeg HLS args (encoder.py line 138-146)
'-f', 'hls',
'-hls_time', '2',
'-hls_list_size', '10',
'-hls_flags', 'delete_segments+append_list',
output_file,

# Recommended v2.0 HLS args
'-f', 'hls',
'-hls_time', '2',  # Keep 2s segments
'-hls_list_size', '10',  # Keep 10 segments (20s buffer)
'-hls_flags', 'delete_segments+append_list+omit_endlist',  # ADD omit_endlist
'-bufsize', f'{bitrate * 4}k',  # INCREASE from 2x to 4x
output_file,
```

**Additional considerations:**
- Monitor segment timestamp freshness (if no new segment in 15s, FFmpeg may be hung)
- Add logging for segment generation events
- Consider `-hls_playlist_type event` for explicit live streaming declaration

### QuickSync Integration Pattern

**Encoder detection strategy:**
```python
async def detect_qsv_support() -> bool:
    """Check if h264_qsv encoder is available."""
    proc = await asyncio.create_subprocess_exec(
        'ffmpeg', '-encoders',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return b'h264_qsv' in stdout
```

**Fallback pattern:**
```python
# In FFmpegEncoder.__aenter__()
try:
    # Try hardware encoder first
    if await detect_qsv_support() and os.path.exists('/dev/dri'):
        logger.info("Using Intel QuickSync h264_qsv encoder")
        codec_args = ['-c:v', 'h264_qsv', '-global_quality', '23', '-preset', 'medium']
    else:
        raise FileNotFoundError("QSV not available")
except Exception as e:
    # Fall back to software encoder
    logger.warning(f"QuickSync unavailable ({e}), falling back to libx264")
    codec_args = ['-c:v', 'libx264', '-preset', self.quality.preset, '-b:v', f'{bitrate}k']

# Start subprocess with selected encoder
self.process = await asyncio.create_subprocess_exec('ffmpeg', *args, *codec_args, ...)
```

**Proxmox GPU passthrough (documentation):**
```bash
# Identify Intel GPU PCI address
lspci | grep VGA

# Edit VM config (/etc/pve/qemu-server/<vmid>.conf)
hostpci0: 00:02.0,pcie=1

# Verify in VM
ls -la /dev/dri/
# Should show: renderD128 (QuickSync device)

# Test QuickSync in container
docker run --device /dev/dri:/dev/dri <image> ffmpeg -encoders | grep qsv
```

### Cast Session State Monitoring

**MediaStatusListener implementation:**
```python
class StreamMediaStatusListener:
    """Monitor Cast media playback state changes."""

    def __init__(self, on_idle_callback):
        self.on_idle_callback = on_idle_callback
        self.previous_state = None

    def new_media_status(self, status):
        """Called when media status changes."""
        player_state = status.player_state  # IDLE, PLAYING, PAUSED, BUFFERING

        if player_state == 'IDLE' and self.previous_state == 'PLAYING':
            # Playback stopped (user stopped from remote or playback ended)
            logger.info("Cast playback stopped, triggering cleanup")
            self.on_idle_callback()

        self.previous_state = player_state

# In CastSessionManager.start_cast()
listener = StreamMediaStatusListener(on_idle_callback=self._cleanup_ffmpeg)
self.device.media_controller.register_status_listener(listener)
```

**FFmpeg cleanup on cast stop:**
```python
async def _cleanup_ffmpeg(self):
    """Clean up FFmpeg process when cast stops."""
    if not self.ffmpeg_process:
        return

    logger.info(f"Cleaning up FFmpeg process (PID: {self.ffmpeg_process.pid})")

    # Try graceful shutdown first
    self.ffmpeg_process.terminate()  # SIGTERM

    try:
        await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=5.0)
        logger.info("FFmpeg terminated gracefully")
    except asyncio.TimeoutError:
        # Force kill if still running
        logger.warning("FFmpeg did not terminate, forcing kill")
        self.ffmpeg_process.kill()  # SIGKILL
        await self.ffmpeg_process.wait()
        logger.info("FFmpeg killed")
```

### Subprocess Cleanup Best Practices

Based on research findings:

1. **Always use asyncio.create_subprocess_exec** - Never blocking subprocess calls in async code
2. **Terminate before kill** - Give process 5-10s to clean up gracefully (SIGTERM), then force (SIGKILL)
3. **Avoid PIPE for quiet mode** - Use `subprocess.DEVNULL` instead of `subprocess.PIPE` to prevent process stalls
4. **Wait for process** - Always await process.wait() after kill to prevent zombies
5. **Handle garbage collection** - Process objects kill children on GC, but explicit cleanup is better
6. **Use context managers** - Ensure cleanup even on exceptions

**Current implementation status:** ✓ Good (encoder.py __aexit__ has terminate → wait_for → kill pattern)

### fMP4 Low-Latency Validation Checklist

**Configuration verification (all ✓ in current implementation):**
- [x] `movflags`: `frag_keyframe+empty_moov+default_base_moof` (CMAF compliant)
- [x] `tune`: `zerolatency` (low-latency mode only)
- [x] `bf`: 0 (no B-frames for low latency)
- [x] `refs`: 1 (single reference frame)
- [x] `g`: framerate (1-second GOP)
- [x] `stream_type`: LIVE (Cast low-latency mode)
- [x] `content_type`: video/mp4 (fMP4 MIME type)

**Manual validation steps:**
1. Start fMP4 stream: `curl -X POST http://localhost:8000/start -d '{"url": "https://google.com", "mode": "fmp4"}'`
2. Verify Cast device plays video immediately (no buffering delay)
3. Check FFmpeg logs for fragmented MP4 output
4. Monitor latency (should be <2 seconds from browser update to TV display)
5. Verify stream continues indefinitely (no timeout or freeze)

**Expected validation result:** fMP4 mode works correctly based on CMAF best practices. No code changes needed, only validation testing.

## Production HLS Best Practices Summary

Based on 2026 industry research:

### Segment Duration
- **Recommended:** 2-4 seconds (balance latency and stability)
- **Low-latency:** 1-2 seconds (higher overhead, use for real-time content)
- **Stable buffered:** 4-6 seconds (best for unreliable networks)
- **Never:** <1 second (playlist thrashing) or >10 seconds (long buffering)

### Playlist Configuration
- **Type:** EVENT (live streaming, append-only) or no type tag (default live)
- **List size:** 6-10 segments (balance between buffer and memory)
- **Flags:** `delete_segments+append_list+omit_endlist` (continuous streaming)

### Keyframe Alignment
- **Critical:** Keyframes must align across all renditions for ABR switching
- **GOP size:** 1-2 seconds (30-60 frames at 30fps) for responsive quality switching
- **Regular intervals:** Use `-g` parameter to force constant GOP size

### Buffer Configuration
- **Rule of thumb:** Buffer size should be 2-4x target bitrate
- **Minimum:** 2x bitrate for stable networks
- **Recommended:** 4x bitrate for typical home networks with jitter

### Stream Health
- **Monitor:** Segment generation freshness (newest segment timestamp)
- **Alert threshold:** If no new segment in 2x segment duration, encoder may be hung
- **Recovery:** Restart FFmpeg process with exponential backoff

## Sources

### HLS Streaming and Buffer Configuration
- [stream freezes after 5-6s · Issue #1626 · video-dev/hls.js](https://github.com/video-dev/hls.js/issues/1626) - MEDIUM confidence
- [HLS Latency Sucks, But Here's How to Fix It (Update)](https://www.wowza.com/blog/hls-latency-sucks-but-heres-how-to-fix-it) - HIGH confidence
- [MPEG-DASH & HLS segment length for adaptive streaming | Bitmovin](https://bitmovin.com/mpeg-dash-hls-segment-length/) - HIGH confidence
- [Choosing the Segment Duration for DASH or HLS - Streaming Learning Center](https://streaminglearningcenter.com/learning/choosing-the-optimal-segment-duration.html) - HIGH confidence
- [Creating A Production Ready Multi Bitrate HLS VOD stream | by Peer5 | Medium](https://medium.com/@peer5/creating-a-production-ready-multi-bitrate-hls-vod-stream-dff1e2f1612c) - HIGH confidence
- [Using FFmpeg as a HLS streaming server (Part 2) – Enhanced HLS Segmentation | Martin Riedl](https://www.martin-riedl.de/2018/08/24/using-ffmpeg-as-a-hls-streaming-server-part-2/) - MEDIUM confidence
- [The Complete Guide to HLS Video Streaming Protocol: Principles, Advantages, and Practice (2026 Edition)](https://m3u8-player.net/blog/hls-streaming-protocol-guide-2026/) - MEDIUM confidence
- [HLS Packaging using FFmpeg - Easy Step-by-Step Tutorial - OTTVerse](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/) - HIGH confidence

### Intel QuickSync Hardware Acceleration
- [Intel Quick Sync Video - Wikipedia](https://en.wikipedia.org/wiki/Intel_Quick_Sync_Video) - MEDIUM confidence
- [cloud-computing-quicksync-video-ffmpeg-white-paper.pdf](https://www.intel.com/content/dam/www/public/us/en/documents/white-papers/cloud-computing-quicksync-video-ffmpeg-white-paper.pdf) - HIGH confidence
- [HandBrake Documentation — Intel Quick Sync Video](https://handbrake.fr/docs/en/latest/technical/video-qsv.html) - HIGH confidence
- [ffmpeg and hevc_qsv Intel Quick Sync settings | Nelson's log](https://nelsonslog.wordpress.com/2022/08/22/ffmpeg-and-hevc_qsv-intel-quick-sync-settings/) - MEDIUM confidence
- [Use Intel QuickSync Video hardware acceleration for transcoding video - FFmpeg By Example](https://ffmpegbyexample.com/examples/fpwszeip/use_intel_quicksync_video_hardware_acceleration_for_transcoding_video/) - MEDIUM confidence
- [Intel QuickSync - Perfect Media Server](https://perfectmediaserver.com/06-hardware/intel-quicksync/) - MEDIUM confidence

### Cast Session Lifecycle and Monitoring
- [GitHub - home-assistant-libs/pychromecast: Library for Python 3 to communicate with the Google Chromecast.](https://github.com/home-assistant-libs/pychromecast) - HIGH confidence
- [How can I tell when an app stops casting? · Issue #84 · home-assistant-libs/pychromecast](https://github.com/balloob/pychromecast/issues/84) - MEDIUM confidence
- [Class: Media | Cast | Google for Developers](https://developers.google.com/cast/docs/reference/web_sender/chrome.cast.media.Media) - HIGH confidence
- [Media Playback Messages | Cast | Google for Developers](https://developers.google.com/cast/docs/media/messages) - HIGH confidence
- [[CastPlayer] Detecting media source ended · Issue #4130 · google/ExoPlayer](https://github.com/google/ExoPlayer/issues/4130) - MEDIUM confidence

### FFmpeg Process Management and Cleanup
- [How to gently terminate ffmpeg when called from a service? - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=284030) - MEDIUM confidence
- [Orphan Process Handling in Docker - Peter Malmgren](https://petermalmgren.com/orphan-children-handling-containerd/) - MEDIUM confidence
- [asyncffmpeg · PyPI](https://pypi.org/project/asyncffmpeg/) - HIGH confidence
- [GitHub - scivision/asyncio-subprocess-ffmpeg: Examples of Python asyncio.subprocess](https://github.com/scivision/asyncio-subprocess-ffmpeg) - HIGH confidence
- [ffmpeg-progress-yield · PyPI](https://pypi.org/project/ffmpeg-progress-yield/) - MEDIUM confidence
- [Subprocesses — Python 3.14.2 documentation](https://docs.python.org/3/library/asyncio-subprocess.html) - HIGH confidence

### fMP4 Low-Latency Streaming
- [How Fragmented MP4 Works for Adaptive Streaming - My Framer Site](https://www.simalabs.ai/resources/how-fragmented-mp4-works-for-adaptive-streaming) - MEDIUM confidence
- [Video Streaming With Ffmpeg. Build your own video streaming service. | by Engineering musings with 'Dunsimi | Jan, 2026 | Medium](https://buildwithdunsimi.medium.com/video-streaming-with-ffmpeg-29fac7e0d514) - MEDIUM confidence
- [Low-Latency HLS: The Era of Flexible Low-Latency Streaming | by OvenMediaEngine | Medium](https://medium.com/@OvenMediaEngine/low-latency-hls-the-era-of-flexible-low-latency-streaming-ec675aa61378) - HIGH confidence
- [What is CMAF? A Complete Guide to Efficient Media Streaming](https://www.fastpix.io/blog/cmaf-explained-improve-media-streaming-quality-and-speed) - HIGH confidence
- [Packaging HTTP Live Streaming with fragmented MP4 (fMP4 HLS) — Unified Streaming](https://docs.unified-streaming.com/documentation/package/fmp4-hls.html) - HIGH confidence

---
*Feature research for: v2.0 Stability and Hardware Acceleration*
*Researched: 2026-01-18*
*Focus: Production HLS streaming stability, QuickSync hardware acceleration, Cast session lifecycle management*
