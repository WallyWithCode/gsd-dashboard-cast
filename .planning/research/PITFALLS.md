# Pitfalls Research: v2.0 Stability and Hardware Acceleration

**Domain:** Web-to-video streaming with Intel QuickSync hardware acceleration
**Researched:** 2026-01-18
**Confidence:** HIGH (QuickSync/VAAPI), HIGH (HLS Buffering), MEDIUM (Process Cleanup), HIGH (Proxmox GPU)

## Critical Pitfalls

### Pitfall 1: HLS Segment Duration vs Buffer Window Mismatch

**What goes wrong:**
HLS streams freeze at exactly 6 seconds (the segment duration) because the player expects a minimum buffer of 3 segments (18 seconds) before starting playback, but the playlist only contains 2-3 segments. When the playlist uses `hls_list_size` too small for the segment duration, players stall waiting for enough buffer depth. The stream appears to load but freezes immediately after the first segment completes.

**Why it happens:**
Developers set `hls_time` (segment duration) without considering the relationship to `hls_list_size` (playlist depth). Players typically maintain a buffer of 3 segments (18-30 seconds) to prevent playback issues during network fluctuations. With 2-second segments and `hls_list_size=10`, you have 20 seconds of buffer (good). But with 6-second segments and `hls_list_size=3`, you only have 18 seconds and the player may not find the next segment fast enough. The current implementation uses `hls_time=2` with `hls_list_size=10` which should work, but if segment duration increases without adjusting list size, freezes occur.

**How to avoid:**
1. Maintain minimum buffer window: `hls_list_size * hls_time >= 18` (at least 3 segments)
2. For 2-second segments: use `hls_list_size=10` (20s buffer) - CURRENT IMPLEMENTATION
3. For 6-second segments: use `hls_list_size=5` (30s buffer minimum)
4. Never reduce `hls_list_size` below 5 for any segment duration
5. Add `-hls_playlist_type event` to prevent #EXT-X-ENDLIST from appearing (enables indefinite streaming)
6. Ensure `delete_segments` flag works correctly to prevent disk overflow
7. Test with actual Cast device player, not just browser HLS.js player (different buffering behavior)

**Warning signs:**
- Stream plays for exactly N seconds then freezes (where N = segment duration)
- Player shows buffering spinner after initial playback
- Cast device displays playback but no new segments load
- FFmpeg continues encoding but Cast device stops requesting segments
- Logs show segment creation but no HTTP requests for new segments

**Phase to address:**
HLS Buffering Fix Phase (v2.0) - This is the current 6-second freeze issue that needs immediate fixing.

**Confidence:** HIGH

**Sources:**
- [HLS Latency Sucks, But Here's How to Fix It](https://www.wowza.com/blog/hls-latency-sucks-but-heres-how-to-fix-it)
- [stream freezes after 5-6s · Issue #1626 · video-dev/hls.js](https://github.com/video-dev/hls.js/issues/1626)
- [Reducing Latency in HLS Streaming: Key Tips](https://www.fastpix.io/blog/reducing-latency-in-hls-streaming)

---

### Pitfall 2: FFmpeg Process Cleanup Race Conditions

**What goes wrong:**
Multiple FFmpeg processes spawn and never terminate, causing VM lockup. When stopping a stream, if FFmpeg is in the middle of encoding a frame or writing a segment, sending SIGTERM doesn't guarantee immediate termination. The process hangs waiting for I/O completion or encoder flush. Meanwhile, new stream requests spawn additional FFmpeg instances. Without proper process tracking and forced cleanup, orphaned processes accumulate until system resources are exhausted. This manifests as: multiple `ffmpeg` processes visible in `ps aux`, CPU pegged at 100% across all processes, and eventual system unresponsiveness.

**Why it happens:**
The current implementation in `encoder.py` uses `process.terminate()` followed by `wait_for(process.wait(), timeout=5.0)` then `process.kill()`. However, race conditions occur when:
1. **Encoding in progress**: FFmpeg receives SIGTERM while encoding a frame, attempts to flush encoder buffers gracefully, takes >5 seconds, gets SIGKILL, leaves segment files in inconsistent state
2. **x11grab source disappears**: If Xvfb context exits before FFmpeg, x11grab crashes (FFmpeg bug #7312), causing segfault instead of clean exit
3. **Segment write mid-operation**: HLS segment is being written when SIGTERM arrives, file lock prevents cleanup, process hangs in uninterruptible sleep
4. **Child process orphaning**: FFmpeg spawns child processes for filters/encoding that may not receive termination signals
5. **Context manager ordering**: If `XvfbManager` exits before `FFmpegEncoder`, the video source disappears causing crash

**How to avoid:**
1. **Graceful stop via stdin 'q' command**: Send 'q\n' to FFmpeg stdin first (graceful stop), wait 2 seconds, then SIGTERM
2. **Fix context manager nesting order**: Ensure FFmpeg exits BEFORE Xvfb (current code is correct, but verify)
3. **Track all child processes**: Use process group termination (`os.killpg()`) to kill FFmpeg and its children
4. **Add process group creation**: Start FFmpeg with `preexec_fn=os.setsid` to create new process group
5. **Implement process registry**: Track all spawned FFmpeg PIDs globally, cleanup on shutdown/error
6. **Reduce kill timeout**: Change 5-second timeout to 3 seconds (encoder flush shouldn't take that long)
7. **Force segment completion**: Use `-hls_flags +temp_file` to write segments to .tmp first, atomically rename on completion
8. **Monitor zombie processes**: Add health check that counts FFmpeg processes, alert if >1 per active stream

**Warning signs:**
- `ps aux | grep ffmpeg` shows multiple processes when only one stream active
- CPU usage doesn't drop after stopping stream
- `top` shows defunct `<ffmpeg>` processes (zombies)
- Disk shows `.ts.tmp` files that never complete
- Subsequent stream starts fail with "device or resource busy"
- VM becomes unresponsive after multiple start/stop cycles
- Log shows "FFmpeg did not terminate gracefully, forcing kill" repeatedly

**Phase to address:**
Process Cleanup Phase (v2.0) - Critical for production stability and multiple stream scenarios.

**Confidence:** HIGH

**Sources:**
- [Race condition: We had to kill ffmpeg to stop it · Issue #13 · imageio/imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg/issues/13)
- [#7312 (crash while encoding from x11grab when source goes away) – FFmpeg](https://trac.ffmpeg.org/ticket/7312)
- [Killing an ffmpeg process kills Streamer · Issue #20 · shaka-project/shaka-streamer](https://github.com/google/shaka-streamer/issues/20)
- [How to gently terminate ffmpeg when called from a service?](https://forums.raspberrypi.com/viewtopic.php?t=284030)

---

### Pitfall 3: Intel QuickSync Driver and Permission Configuration

**What goes wrong:**
Intel QuickSync hardware acceleration fails with cryptic errors like "Error initializing an internal MFX session: unsupported (-3)", "Failed to initialize VAAPI connection: -1 (generic error)", or "Permission denied" when accessing `/dev/dri/renderD128`. FFmpeg falls back to software encoding, pegging CPU at 100% and defeating the entire purpose of hardware acceleration. In Docker containers, the issue is even more insidious because FFmpeg may silently fall back to software encoding without obvious error messages.

**Why it happens:**
Multiple configuration layers must align perfectly for QuickSync to work:
1. **Missing kernel drivers**: i915 kernel module not loaded or wrong version
2. **Missing userspace drivers**: VAAPI driver not installed (libva-intel-driver for old CPUs, intel-media-va-driver for new)
3. **Wrong VAAPI driver selected**: FFmpeg tries iHD driver but hardware needs i965 (or vice versa)
4. **Permission denied on /dev/dri**: User/container not in `render` or `video` group
5. **Docker GID mismatch**: Host's render group is GID 109, container's is GID 115, device access fails
6. **CPU generation incompatibility**: Trying to use QuickSync on <4th gen Intel (not supported)
7. **FFmpeg not built with QSV support**: FFmpeg compiled without `--enable-libmfx` or `--enable-libvpl`
8. **Proxmox GPU not passed through**: VM doesn't have access to iGPU at all

**How to avoid:**
1. **Verify CPU generation**: QuickSync requires Intel 4th gen (Haswell) or newer - check `lscpu`
2. **Check driver loading**: `lsmod | grep i915` should show i915 with use count >1
3. **Install correct VAAPI driver**:
   - Intel Gen 8+ (Broadwell+): `apt install intel-media-va-driver` (iHD driver)
   - Intel Gen <8: `apt install i965-va-driver` (i965 driver)
4. **Verify VAAPI works**: `vainfo` should show device and supported profiles without errors
5. **Set driver explicitly**: Add `LIBVA_DRIVER_NAME=iHD` (or `i965`) environment variable if auto-detection fails
6. **Fix Docker permissions**:
   - Get host render GID: `getent group render` (e.g., 109)
   - Add to docker-compose: `group_add: ["109"]` (use numeric GID)
   - Mount device: `devices: ["/dev/dri:/dev/dri"]`
7. **Verify FFmpeg QSV support**: `ffmpeg -encoders | grep qsv` should list h264_qsv, hevc_qsv
8. **Test encoding**: `ffmpeg -f lavfi -i testsrc -c:v h264_vaapi -vaapi_device /dev/dri/renderD128 -t 5 test.mp4`
9. **Add fallback detection**: If QuickSync init fails, log clear error and fall back to libx264 with warning

**Warning signs:**
- FFmpeg output shows `[libx264 @ ...]` instead of `[h264_vaapi @ ...]` or `[h264_qsv @ ...]`
- `vainfo` command fails with "failed to initialize display" or "permission denied"
- `/dev/dri/` directory doesn't exist or is empty
- CPU usage at 100% despite attempting hardware encoding
- Error messages mentioning "MFX session", "VAAPI connection", or "unsupported"
- Docker container logs show "Operation not permitted" for /dev/dri access

**Phase to address:**
QuickSync Integration Phase (v2.0) - Must be configured correctly before claiming hardware acceleration support.

**Confidence:** HIGH

**Sources:**
- [quicksync via ffmpeg - VideoHelp Forum](https://forum.videohelp.com/threads/382511-quicksync-via-ffmpeg)
- [Videos: Fix installation of Intel Quick Sync drivers for hardware transcoding · Issue #2700 · photoprism/photoprism](https://github.com/photoprism/photoprism/issues/2700)
- [Hardware acceleration doesn't work when the container's (hardcoded) render group's GID doesn't match the host's · Issue #2739 · photoprism/photoprism](https://github.com/photoprism/photoprism/issues/2739)
- [FFmpeg and oneVPL-intel-gpu (or quicksync) / Arch Linux Forums](https://bbs.archlinux.org/viewtopic.php?id=279799)
- [Hardware video acceleration - ArchWiki](https://wiki.archlinux.org/title/Hardware_video_acceleration)

---

### Pitfall 4: Proxmox GPU Passthrough IOMMU Configuration

**What goes wrong:**
Intel iGPU is not accessible inside the VM even after Proxmox GPU passthrough is configured. `/dev/dri` doesn't appear in the VM, or attempting to access it fails with errors. This happens because Proxmox GPU passthrough has multiple layers of configuration that must all be correct: BIOS settings, bootloader configuration, IOMMU grouping, and VM hardware settings. Missing any single step means the GPU isn't available to the VM, which then can't access it for Docker containers.

**Why it happens:**
Proxmox GPU passthrough requires a complex configuration chain:
1. **BIOS VT-d disabled**: Intel VT-d (virtualization for directed I/O) must be enabled in BIOS
2. **IOMMU not enabled in kernel**: Must add `intel_iommu=on` to GRUB bootloader
3. **IOMMU group conflicts**: iGPU may share IOMMU group with other critical devices, preventing passthrough
4. **VM not configured for passthrough**: GPU not added to VM in Proxmox web UI
5. **Exclusive access conflict**: When GPU is passed to VM, neither host nor other VMs can use it
6. **Driver conflicts in VM**: VM tries to use GPU but doesn't have correct drivers installed

Additionally, there's confusion between **PCI passthrough** (full GPU to VM) and **LXC device mapping** (device node sharing). For Docker containers, you need the VM approach: passthrough GPU to VM via PCI, then mount /dev/dri into Docker container.

**How to avoid:**
1. **Enable VT-d in BIOS**: Required for any IOMMU operations
2. **Configure GRUB for IOMMU**:
   - Edit `/etc/default/grub`
   - Add to `GRUB_CMDLINE_LINUX_DEFAULT`: `quiet intel_iommu=on iommu=pt`
   - Run `update-grub` and reboot Proxmox host
3. **Verify IOMMU enabled**: `dmesg | grep -e DMAR -e IOMMU` should show "IOMMU enabled"
4. **Check IOMMU groups**: `find /sys/kernel/iommu_groups/ -type l` to see device groupings
5. **Verify iGPU has own IOMMU group**: If shared with other devices, passthrough may fail
6. **Add GPU to VM in Proxmox**:
   - VM → Hardware → Add → PCI Device
   - Select Intel iGPU (usually 00:02.0)
   - Check "All Functions" if available
   - Check "Primary GPU" only if you want display output (usually NO for headless)
7. **Inside VM**: Verify `/dev/dri/` exists and contains `card0` and `renderD128`
8. **Install drivers in VM**: `apt install intel-media-va-driver vainfo`
9. **Test in VM**: `vainfo` should show Intel device and capabilities
10. **Then passthrough to Docker**: Add device and group to docker-compose

**Warning signs:**
- Proxmox host shows iGPU in `lspci` but VM doesn't
- `dmesg | grep IOMMU` shows nothing (IOMMU not enabled)
- VM shows PCI device but `/dev/dri` doesn't exist
- `lspci` in VM shows GPU but driver not loaded
- Attempting `vainfo` in VM fails with "cannot open display"
- Proxmox web UI doesn't show GPU in available PCI devices for VM

**Phase to address:**
Proxmox GPU Passthrough Documentation Phase (v2.0) - Prerequisites before QuickSync can work.

**Confidence:** HIGH

**Sources:**
- [GPU Passthrough with Proxmox: A Practical Guide](https://diymediaserver.com/post/gpu-passthrough-proxmox-quicksync-guide/)
- [Intel N100/iGPU Passthrough to VM and use with Docker | Proxmox Support Forum](https://forum.proxmox.com/threads/intel-n100-igpu-passthrough-to-vm-and-use-with-docker.140370/)
- [Quick Sync and iGPU passthrough - Perfect Media Server](https://perfectmediaserver.com/05-advanced/passthrough-igpu-gvtg/)
- [Intel NUC GPU passthrough in Proxmox 6.1 with Plex and Docker · Jack Cuthbert](https://jackcuthbert.dev/blog/intel-nuc-gpu-passthrough-in-proxmox-plex-docker)

---

### Pitfall 5: pychromecast Callback Timing and Device-Initiated Stop Detection

**What goes wrong:**
When a user stops casting from the Cast device (TV remote, Google Home app), the application doesn't detect it and FFmpeg continues encoding indefinitely, wasting CPU resources. The stream becomes orphaned: FFmpeg runs, server serves HLS segments, but nobody is watching. Without device-initiated stop detection, the only way to stop encoding is the duration timeout or explicit webhook call. In v1.1, there's no monitoring of Cast session state, so device disconnections are invisible to the application.

**Why it happens:**
The current implementation doesn't register status listeners for Cast session changes. pychromecast provides `MediaStatusListener` and `ConnectionStatusListener` callbacks, but they must be explicitly registered. Without these listeners:
- DISCONNECTED events are never received
- IDLE state transitions (when playback stops) are missed
- Application has no visibility into actual playback state
- Context manager exits only when Python code explicitly exits the `async with` block

Additionally, pychromecast v14.0.0 introduced breaking changes to callback signatures requiring kwarg-only arguments, and media status listeners don't work correctly with async discovery in some versions.

**How to avoid:**
1. **Register ConnectionStatusListener**: Implement callback for `new_connection_status()` to detect DISCONNECTED
2. **Register MediaStatusListener**: Implement callback for `new_media_status()` to detect IDLE state
3. **Use asyncio.Event for stop signaling**: Replace `await asyncio.sleep(float('inf'))` with `stop_event.wait()`
4. **Set stop_event when DISCONNECTED**: In listener callback, call `stop_event.set()` to break streaming loop
5. **Handle callback in thread-safe way**: pychromecast callbacks run in different thread, use `loop.call_soon_threadsafe()`
6. **Test with actual device stop**: Stop casting from TV remote, verify FFmpeg terminates within 5 seconds
7. **Add reconnection grace period**: Don't stop immediately on DISCONNECTED, wait 10 seconds (may be temporary network blip)
8. **Log all state transitions**: Debug visibility into what's happening with Cast session
9. **Check pychromecast version**: Ensure >= 14.0.0 for latest callback APIs, update callback signatures if needed

**Warning signs:**
- Stopping cast from TV remote doesn't terminate stream
- FFmpeg continues running after "Cast device disconnected" in logs
- Multiple orphaned FFmpeg processes accumulate over time
- CPU usage remains high even when TV shows "Ready to cast" screen
- Logs show "Session not active" but FFmpeg still running
- No log messages when stopping playback from device

**Phase to address:**
Device-Initiated Stop Detection Phase (v2.0) - Critical for resource management and user experience.

**Confidence:** MEDIUM (pychromecast callback APIs have version-specific quirks)

**Sources:**
- [More Documentation Needed to Avoid RunTime errors · Issue #560 · home-assistant-libs/pychromecast](https://github.com/home-assistant-libs/pychromecast/issues/560)
- [Media status listener doesn't work for async discovery · Issue #259 · home-assistant-libs/pychromecast](https://github.com/home-assistant-libs/pychromecast/issues/259)
- [Release 14.0.0 · home-assistant-libs/pychromecast](https://github.com/home-assistant-libs/pychromecast/releases/tag/14.0.0)
- [[pychromecast.controllers.media] Exception thrown when calling media status callback · Issue #35780 · home-assistant/core](https://github.com/home-assistant/core/issues/35780)

---

### Pitfall 6: HLS delete_segments Flag Failures

**What goes wrong:**
HLS `.ts` segment files accumulate on disk despite `hls_flags delete_segments` being set. Over time, `/tmp/streams/` fills with hundreds of orphaned segment files, eventually filling the disk and causing system failures. This is particularly insidious in long-running streams or when streams are stopped abruptly without cleanup. The current implementation uses `-hls_flags delete_segments+append_list` but this can fail on file locking issues, permission problems, or platform-specific bugs.

**Why it happens:**
The `delete_segments` flag has several known failure modes:
1. **Windows file locking**: On Windows, FFmpeg can't delete segments it's currently reading, "Permission denied" errors
2. **Race condition in deletion**: FFmpeg tries to delete segment while HTTP server is serving it to Cast device
3. **Crash without cleanup**: If FFmpeg crashes (e.g., x11grab source disappears), segments never deleted
4. **Manual termination**: Sending SIGKILL doesn't give FFmpeg chance to run cleanup
5. **Filesystem permissions**: User running FFmpeg doesn't have write permissions to output directory
6. **NFS/network filesystems**: Deletion may fail on network-mounted filesystems with stale file handles

Additionally, the current implementation's cleanup in `__aexit__()` only removes `.m3u8` and matching `.ts` files, but if the process crashes before `__aexit__()` runs, files remain forever.

**How to avoid:**
1. **Add startup cleanup**: On service start, delete all files in `/tmp/streams/` older than 1 hour
2. **Use temp_file flag**: Add `-hls_flags +temp_file` to write segments to `.tmp` first, atomic rename prevents serving partial files
3. **Increase segment list size**: More segments in playlist = more time before deletion needed = fewer race conditions
4. **Background cleanup task**: Run separate asyncio task that periodically scans `/tmp/streams/` and deletes old segments
5. **Verify deletion works**: In testing, check that segment count stabilizes (doesn't keep growing)
6. **Monitor disk usage**: Alert if `/tmp/streams/` exceeds 1GB (indicates cleanup failure)
7. **Fallback to manual cleanup**: If `delete_segments` fails, implement Python-based cleanup logic
8. **Use memory-based tmpfs**: Mount `/tmp/streams/` on tmpfs (RAM disk) so OS cleanup handles orphans on reboot
9. **Test crash scenarios**: Kill FFmpeg with `kill -9`, verify segments eventually get cleaned up

**Warning signs:**
- `ls /tmp/streams/*.ts | wc -l` shows hundreds or thousands of files
- Disk usage of `/tmp/streams/` grows over time
- FFmpeg logs show "Failed to delete segment" errors
- After stream stops, old segments remain on disk
- Service crashes with "No space left on device"
- HTTP 404 errors for old segments that should have been deleted

**Phase to address:**
HLS Buffering Fix Phase (v2.0) - Cleanup issues compound the buffering problems.

**Confidence:** HIGH

**Sources:**
- [-f hls -hls_flags delete_segments broken on windows (locking issue) - FFmpeg](https://ffmpeg.zeranoe.com/forum/viewtopic.php?t=4916)
- [PATCH] delete the old segment file from hls list](https://ffmpeg-devel.ffmpeg.narkive.com/gAocPWVn/patch-delete-the-old-segment-file-from-hls-list)
- [HLS files are not deleting from server · Issue #4139 · ant-media/Ant-Media-Server](https://github.com/ant-media/Ant-Media-Server/issues/4139)

---

### Pitfall 7: fMP4 Fragmentation Flags for Cast Compatibility

**What goes wrong:**
fMP4 low-latency streams fail to play on Cast devices with errors like "Media could not be loaded" or playback starts but stutters/freezes. The Cast device's media player expects specific fragmentation structure in fMP4 files: `moov` box must come first (before any media data), fragments must start with keyframes (`moof` boxes), and base decode times must be set correctly. Without the exact combination of FFmpeg movflags, the generated MP4 doesn't meet Cast's streaming requirements.

**Why it happens:**
Fragmented MP4 has strict structural requirements for streaming:
- **empty_moov**: Metadata (moov box) at beginning with no samples, all media in fragments
- **frag_keyframe**: Each fragment starts with a keyframe (I-frame), required for seeking
- **default_base_moof**: Base decode times relative to moof box, not moov (streaming requirement)

The current implementation uses these flags correctly: `-movflags frag_keyframe+empty_moov+default_base_moof`. However, several additional issues can break fMP4 playback:
1. **Missing keyframe intervals**: Must ensure GOP size matches fragment size
2. **entry_count not zero**: Per MP4 spec, fragmented files must have entry_count=0 in certain boxes
3. **Server MIME type**: Must serve with `Content-Type: video/mp4`, not `application/octet-stream`
4. **Range request support**: Cast devices send `Range:` headers, server must support partial content
5. **CORS headers**: Fragmented MP4 requires same CORS headers as HLS (Range, Content-Type)

**How to avoid:**
1. **Keep existing movflags**: `-movflags frag_keyframe+empty_moov+default_base_moof` is correct
2. **Ensure GOP alignment**: Fragment duration should align with keyframe interval: `-g <framerate>` for 1-second GOPs
3. **Add fragment duration**: Consider `-frag_duration <microseconds>` to control fragment size explicitly
4. **Test with ffprobe**: `ffprobe -show_boxes stream.mp4` should show moov before first moof
5. **Verify server MIME type**: aiohttp should serve .mp4 with `Content-Type: video/mp4`
6. **Enable Range support**: Ensure StreamingServer handles `Range:` headers (aiohttp FileResponse does this)
7. **Test on actual Cast device**: Browser may play broken fMP4 that Cast device rejects
8. **Check fragment boundaries**: Every moof should have a keyframe, verify with `ffprobe -show_frames`
9. **Monitor for stuttering**: If playback stutters every N seconds, fragment alignment issue

**Warning signs:**
- fMP4 mode streams show "Media could not be loaded" on Cast device
- Playback starts but freezes after first fragment
- Browser plays fine but Cast device fails (MIME type or CORS issue)
- Cast device shows buffering spinner continuously
- Logs show Cast device requesting first fragment repeatedly (failing to parse)
- Switching from fMP4 to HLS mode works (indicates fMP4-specific issue)

**Phase to address:**
fMP4 Validation Phase (v2.0) - Must verify low-latency mode actually works before claiming feature complete.

**Confidence:** MEDIUM (Cast-specific fMP4 requirements may have undocumented quirks)

**Sources:**
- [In-browser live video using Fragmented MP4 | by Vlad Poberezhny | Medium](https://medium.com/@vlad.pbr/in-browser-live-video-using-fragmented-mp4-3aedb600a07e)
- [How Fragmented MP4 Works for Adaptive Streaming](https://www.simalabs.ai/resources/how-fragmented-mp4-works-for-adaptive-streaming)
- [1077264 - Fragmented MP4 generated by mp4fragment utility do not play](https://bugzilla.mozilla.org/show_bug.cgi?id=1077264)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using libx264 instead of h264_vaapi during development | Works everywhere, no driver config | 100% CPU usage, can't scale to multiple streams | Only for initial development, never production |
| Ignoring segment cleanup failures | Simple implementation | Disk fills, system crashes | Never - must implement fallback cleanup |
| Not monitoring Cast session state | Simpler code, fewer callbacks | Orphaned FFmpeg processes, wasted resources | Never for production - critical resource leak |
| Hardcoding render group GID in Dockerfile | Works on your system | Breaks on other hosts with different GID | Never - always use dynamic GID or privileged mode |
| Using `-hls_time 6` instead of 2 | Better compression efficiency | 18-30s latency, freezing issues | Only for non-interactive VOD content |
| Skipping IOMMU configuration in Proxmox | Easier VM setup | Hardware acceleration never works | Never if planning to use QuickSync |
| Not implementing process group termination | Simpler subprocess code | Orphaned child processes, zombie FFmpeg | Never - process cleanup must be bulletproof |
| Using LIBVA_DRIVER_NAME=iHD without testing | Works on newest hardware | Fails on older CPUs, silent fallback to software | Only if you control deployment hardware exactly |
| Skipping vainfo verification in health checks | One less dependency | QuickSync silently fails, no monitoring visibility | Never for production claiming HW acceleration |
| Using asyncio.sleep(float('inf')) for indefinite streaming | Simplest possible implementation | Can't detect device-initiated stops | Only for MVP with manual stop via webhook |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Intel QuickSync VAAPI | Assuming iHD driver works on all Intel CPUs | Check CPU generation: Gen 8+ uses iHD, older uses i965, set LIBVA_DRIVER_NAME explicitly |
| Docker /dev/dri permissions | Mounting device without group membership | Get host render GID with `getent group render`, add to container with `group_add: ["<GID>"]` |
| Proxmox GPU passthrough | Assuming GPU is available after adding to VM | Must enable VT-d in BIOS, enable IOMMU in GRUB, verify iGPU has own IOMMU group |
| pychromecast session monitoring | Relying on context manager for cleanup | Must register MediaStatusListener and ConnectionStatusListener for device-initiated events |
| FFmpeg process termination | Using only SIGTERM | Send 'q' to stdin first, then SIGTERM, then SIGKILL with timeouts between each |
| HLS segment cleanup | Relying only on delete_segments flag | Implement startup cleanup task and background cleanup for orphaned files |
| fMP4 streaming to Cast | Using default MP4 muxer settings | Must use exact flags: frag_keyframe+empty_moov+default_base_moof |
| FFmpeg x11grab with context managers | Exiting Xvfb before FFmpeg | Always ensure FFmpeg exits BEFORE Xvfb to prevent segfault (bug #7312) |
| HLS buffer configuration | Setting hls_time without considering hls_list_size | Maintain buffer window: hls_list_size * hls_time >= 18 seconds |
| VAAPI encoder testing | Testing only with ffmpeg command line | Must test full pipeline: encode → serve → Cast device playback (different requirements) |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Software encoding with libx264 | CPU at 100% for single stream | Enable QuickSync/VAAPI hardware acceleration | 2 concurrent streams = VM lockup |
| No FFmpeg process monitoring | Gradual resource exhaustion | Track PIDs globally, alert if count > active streams | After 5-10 start/stop cycles |
| Synchronous FFmpeg termination | Stop requests take 5+ seconds | Send 'q' to stdin for instant graceful stop | When stopping multiple streams |
| HLS segment accumulation | Disk usage grows over time | Implement background cleanup task checking /tmp/streams/ | After 24 hours runtime |
| Single-threaded encoding | Can't utilize multiple CPU cores | Use `-threads <N>` for software encoding (hardware uses GPU) | HD+ streams with CPU encoding |
| No segment file limits | Infinite .ts files created | Set `-hls_list_size` and enable `delete_segments` | Long-running streams >1 hour |
| Missing process group cleanup | Orphaned child processes | Start FFmpeg with `preexec_fn=os.setsid`, kill with `os.killpg()` | After crashes or force kills |
| Cast session without timeout | Sessions never expire | Implement inactivity timeout and session monitoring | After device disconnects |
| Not using temp_file flag | Serving partial/corrupt segments | Add `-hls_flags +temp_file` for atomic segment writes | Under network load/latency |
| Single VAAPI device assumption | Fails when /dev/dri has multiple devices | Explicitly specify `-vaapi_device /dev/dri/renderD128` | Multi-GPU systems |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Running Docker privileged for /dev/dri access | Container escape, full host access | Use device mapping + group_add instead of privileged mode |
| Not validating VAAPI device availability | Exposing system information via errors | Check vainfo in health checks, sanitize driver errors in API responses |
| Serving /tmp/streams/ directory directly | Directory traversal, accessing arbitrary files | Use explicit file serving, never serve parent directory |
| Leaving debug FFmpeg logs in production | Exposing stream URLs, device IPs, auth tokens | Disable FFmpeg stderr logging or sanitize output |
| Not rate-limiting stream start requests | Resource exhaustion DoS | Limit concurrent streams, add rate limiting per IP |
| Exposing Proxmox GPU passthrough to multiple VMs | VM escape via GPU vulnerability | Pass iGPU to single trusted VM only |
| Using world-readable /dev/dri permissions (0666) | Any process can use GPU | Use proper group membership, mode 0660 |
| Not sanitizing Cast device names | Log injection attacks | Sanitize device names before logging |
| Allowing arbitrary segment durations | Disk filling attack with huge segments | Limit hls_time to reasonable range (1-10 seconds) |
| Exposing FFmpeg version in errors | Information disclosure for exploit targeting | Sanitize FFmpeg errors, don't expose version to API |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No feedback when QuickSync unavailable | User expects HW acceleration but gets CPU pegging | Log clear warning "QuickSync not available, using software encoding", expose in /status endpoint |
| Stream continues after device stop | Wasted resources, confusion why CPU still high | Implement device-initiated stop detection, show active streams in status |
| No indication of HLS vs fMP4 mode | User doesn't know which latency to expect | Include mode in /status response, log mode selection clearly |
| Silent fallback to software encoding | User thinks they have HW accel but don't | Fail loudly if QuickSync requested but unavailable, require explicit fallback |
| Orphaned segments filling disk | System failure with no warning | Monitor disk usage, expose in health check, alert before critical |
| FFmpeg process not stopping | User calls /stop but encoding continues | Implement timeout for stop operation, expose error if cleanup fails |
| No visibility into GPU usage | Can't tell if hardware acceleration working | Add GPU utilization to /status endpoint (from intel_gpu_top or similar) |
| 6-second freeze looks like network issue | User blames WiFi instead of config | Fix HLS buffering, add player-side buffering metrics to logs |
| No indication of Proxmox passthrough status | User doesn't know if GPU is available to VM | Add /dev/dri device check to health endpoint, fail startup if missing and QSV required |
| Cast device disconnect looks like error | User doesn't know if they stopped it or system crashed | Distinguish device-initiated stop vs error in logs and status |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **QuickSync Integration:** Often missing driver verification — run `vainfo` in health check and fail if QuickSync expected but unavailable
- [ ] **Docker /dev/dri Access:** Often using wrong GID — verify render group GID matches host with `getent group render` inside container
- [ ] **FFmpeg Process Cleanup:** Often only using SIGTERM — verify zombie processes don't accumulate with `ps aux | grep ffmpeg` after 10 start/stop cycles
- [ ] **HLS Segment Deletion:** Often relying only on delete_segments flag — verify `/tmp/streams/` doesn't grow over time with long-running stream
- [ ] **Device-Initiated Stop:** Often missing session listeners — stop cast from TV remote, verify FFmpeg terminates within 10 seconds
- [ ] **fMP4 Validation:** Often only tested in browser — test actual fMP4 playback on Cast device, not just Chrome
- [ ] **Proxmox IOMMU:** Often missing bootloader config — verify `dmesg | grep IOMMU` shows enabled before claiming GPU passthrough works
- [ ] **Context Manager Ordering:** Often exits Xvfb before FFmpeg — verify FFmpeg __aexit__ called before XvfbManager __aexit__ (no x11grab crash)
- [ ] **VAAPI Driver Selection:** Often assumes auto-detection works — explicitly set LIBVA_DRIVER_NAME and verify with vainfo
- [ ] **Process Group Termination:** Often only kills parent FFmpeg — verify no orphaned child processes with `pstree -p <ffmpeg_pid>` before kill
- [ ] **HLS Buffer Window:** Often sets hls_time without checking hls_list_size — verify `hls_list_size * hls_time >= 18` in config
- [ ] **Segment Cleanup on Crash:** Often only cleans in __aexit__ — verify startup cleanup removes old segments from previous crashed instances

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| HLS 6-second freeze | LOW | Increase hls_list_size from 10 to 15, test with actual Cast device, verify no freezing |
| Multiple FFmpeg processes | LOW | Kill all: `pkill -9 ffmpeg`, restart service, implement process monitoring |
| QuickSync driver missing | MEDIUM | Install intel-media-va-driver, verify with vainfo, restart Docker container |
| Docker render GID mismatch | LOW | Get host GID: `getent group render`, update docker-compose group_add, recreate container |
| Proxmox IOMMU not enabled | MEDIUM | Edit /etc/default/grub, add intel_iommu=on, update-grub, reboot host (downtime required) |
| Orphaned HLS segments | LOW | Manual cleanup: `rm /tmp/streams/*.ts`, implement background cleanup task |
| pychromecast no disconnect detection | MEDIUM | Add MediaStatusListener and ConnectionStatusListener, implement asyncio.Event stop signal |
| FFmpeg process won't terminate | LOW | Use `kill -9 <pid>`, implement stdin 'q' command for graceful stop |
| fMP4 playback fails | LOW | Verify movflags in ffmpeg command, test with ffprobe, check server MIME type |
| x11grab crash on stop | MEDIUM | Fix context manager nesting order, ensure FFmpeg exits before Xvfb |
| VAAPI wrong driver (iHD vs i965) | LOW | Set LIBVA_DRIVER_NAME environment variable explicitly, restart container |
| GPU not visible in VM | HIGH | Verify IOMMU groups, reconfigure Proxmox VM hardware, may need host reboot |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| HLS 6-second freeze | HLS Buffering Fix | Test stream for 5+ minutes, verify no freezing on Cast device |
| FFmpeg process cleanup race | Process Cleanup | Kill stream 10 times, verify `ps aux \| grep ffmpeg` shows 0 processes |
| QuickSync driver/permissions | QuickSync Integration | Run vainfo in container, verify device access, encode test video |
| Proxmox IOMMU configuration | Proxmox GPU Passthrough Docs | Verify /dev/dri in VM, dmesg shows IOMMU enabled |
| pychromecast disconnect detection | Device-Initiated Stop | Stop from TV remote, verify FFmpeg terminates within 10s |
| HLS segment cleanup failures | HLS Buffering Fix | Run stream for 1 hour, verify /tmp/streams/ size stable |
| fMP4 fragmentation issues | fMP4 Validation | Test fMP4 mode on Cast device, verify no stuttering/freezing |
| FFmpeg x11grab crash | Process Cleanup | Verify context manager ordering, test forced Xvfb termination |
| VAAPI driver selection | QuickSync Integration | Test both iHD and i965, verify correct driver loads |
| Process group orphaning | Process Cleanup | Check pstree after FFmpeg kill, verify no orphaned children |
| Docker render GID mismatch | QuickSync Integration | Test on fresh system, verify /dev/dri access without privileged |
| HLS buffer window too small | HLS Buffering Fix | Calculate hls_list_size * hls_time >= 18, adjust if needed |

## Sources

### Intel QuickSync / VAAPI
- [quicksync via ffmpeg - VideoHelp Forum](https://forum.videohelp.com/threads/382511-quicksync-via-ffmpeg)
- [Videos: Fix installation of Intel Quick Sync drivers for hardware transcoding · Issue #2700 · photoprism/photoprism](https://github.com/photoprism/photoprism/issues/2700)
- [FFmpeg and oneVPL-intel-gpu (or quicksync) / Arch Linux Forums](https://bbs.archlinux.org/viewtopic.php?id=279799)
- [Hardware video acceleration - ArchWiki](https://wiki.archlinux.org/title/Hardware_video_acceleration)
- [HardwareVideoAcceleration - Debian Wiki](https://wiki.debian.org/HardwareVideoAcceleration)
- [i965 vs iHD driver · Issue #801 · intel/media-driver](https://github.com/intel/media-driver/issues/801)

### Docker /dev/dri Permissions
- [Hardware acceleration doesn't work when the container's (hardcoded) render group's GID doesn't match the host's · Issue #2739 · photoprism/photoprism](https://github.com/photoprism/photoprism/issues/2739)
- [Access to /dev/dri/renderD128 fails in immich-server docker container · Discussion #13563](https://github.com/immich-app/immich/discussions/13563)
- [Incorrect permissions for /dev/dri · Issue #207 · linuxserver/docker-plex](https://github.com/linuxserver/docker-plex/issues/207)
- [/dev/dri/renderD128 now owned by "render" group, plex missing permission · Issue #211 · linuxserver/docker-plex](https://github.com/linuxserver/docker-plex/issues/211)

### HLS Buffering and Segment Issues
- [HLS Latency Sucks, But Here's How to Fix It](https://www.wowza.com/blog/hls-latency-sucks-but-heres-how-to-fix-it)
- [stream freezes after 5-6s · Issue #1626 · video-dev/hls.js](https://github.com/video-dev/hls.js/issues/1626)
- [Reducing Latency in HLS Streaming: Key Tips](https://www.fastpix.io/blog/reducing-latency-in-hls-streaming)
- [HLS Packaging using FFmpeg - Easy Step-by-Step Tutorial - OTTVerse](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/)
- [-f hls -hls_flags delete_segments broken on windows (locking issue) - FFmpeg](https://ffmpeg.zeranoe.com/forum/viewtopic.php?t=4916)
- [[PATCH] delete the old segment file from hls list](https://ffmpeg-devel.ffmpeg.narkive.com/gAocPWVn/patch-delete-the-old-segment-file-from-hls-list)

### FFmpeg Process Cleanup
- [Race condition: We had to kill ffmpeg to stop it · Issue #13 · imageio/imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg/issues/13)
- [#7312 (crash while encoding from x11grab when source goes away) – FFmpeg](https://trac.ffmpeg.org/ticket/7312)
- [Killing an ffmpeg process kills Streamer · Issue #20 · shaka-project/shaka-streamer](https://github.com/google/shaka-streamer/issues/20)
- [How to gently terminate ffmpeg when called from a service?](https://forums.raspberrypi.com/viewtopic.php?t=284030)

### pychromecast Callbacks
- [More Documentation Needed to Avoid RunTime errors · Issue #560 · home-assistant-libs/pychromecast](https://github.com/home-assistant-libs/pychromecast/issues/560)
- [Media status listener doesn't work for async discovery · Issue #259 · home-assistant-libs/pychromecast](https://github.com/home-assistant-libs/pychromecast/issues/259)
- [Release 14.0.0 · home-assistant-libs/pychromecast](https://github.com/home-assistant-libs/pychromecast/releases/tag/14.0.0)
- [[pychromecast.controllers.media] Exception thrown when calling media status callback · Issue #35780 · home-assistant/core](https://github.com/home-assistant/core/issues/35780)

### fMP4 Fragmentation
- [In-browser live video using Fragmented MP4 | by Vlad Poberezhny | Medium](https://medium.com/@vlad.pbr/in-browser-live-video-using-fragmented-mp4-3aedb600a07e)
- [How Fragmented MP4 Works for Adaptive Streaming](https://www.simalabs.ai/resources/how-fragmented-mp4-works-for-adaptive-streaming)
- [1077264 - Fragmented MP4 generated by mp4fragment utility do not play](https://bugzilla.mozilla.org/show_bug.cgi?id=1077264)

### Proxmox GPU Passthrough
- [GPU Passthrough with Proxmox: A Practical Guide](https://diymediaserver.com/post/gpu-passthrough-proxmox-quicksync-guide/)
- [Intel N100/iGPU Passthrough to VM and use with Docker | Proxmox Support Forum](https://forum.proxmox.com/threads/intel-n100-igpu-passthrough-to-vm-and-use-with-docker.140370/)
- [Quick Sync and iGPU passthrough - Perfect Media Server](https://perfectmediaserver.com/05-advanced/passthrough-igpu-gvtg/)
- [Intel NUC GPU passthrough in Proxmox 6.1 with Plex and Docker · Jack Cuthbert](https://jackcuthbert.dev/blog/intel-nuc-gpu-passthrough-in-proxmox-plex-docker)

---
*Pitfalls research for: v2.0 Stability and Hardware Acceleration*
*Researched: 2026-01-18*
*Focused on: Intel QuickSync integration, HLS buffering fixes, process cleanup, device-initiated stop detection, Proxmox GPU passthrough*
