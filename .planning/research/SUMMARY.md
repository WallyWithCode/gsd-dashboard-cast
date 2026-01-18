# Project Research Summary

**Project:** gsd-dashboard-cast v2.0 Stability and Hardware Acceleration
**Domain:** Production HLS streaming with hardware-accelerated encoding and robust lifecycle management
**Researched:** 2026-01-18
**Confidence:** HIGH

## Executive Summary

v2.0 addresses four critical production issues that prevent the current v1.1 system from scaling beyond single-stream usage: HLS buffering freezes, orphaned FFmpeg processes after device-initiated cast stops, CPU-bound software encoding, and lack of Proxmox GPU passthrough documentation. Research reveals these are well-understood problems with proven solutions: increase HLS buffer window from 20s to 40s with deletion threshold, implement pychromecast MediaStatusListener callbacks for device stop detection, integrate Intel QuickSync h264_qsv encoder with graceful fallback to software encoding, and provide comprehensive Proxmox IOMMU configuration guide.

The recommended approach follows a risk-escalation pattern: start with minimal-change HLS configuration tuning (fix 6-second freeze), validate existing fMP4 low-latency mode, add Cast session state monitoring foundation, implement robust process lifecycle tracking, and finally integrate QuickSync hardware acceleration with proper fallback paths. Each phase is independently deployable and provides value even if later phases are deferred. Critical success factors: proper context manager nesting order (FFmpeg exits before Xvfb to prevent x11grab crashes), Docker render group GID matching for /dev/dri access, and timeout-based cleanup escalation (stdin 'q' → SIGTERM → SIGKILL).

Key risk mitigation: all hardware acceleration features must gracefully degrade to software encoding. QuickSync availability varies by deployment (Proxmox VM vs bare metal, Intel CPU generation, driver installation), so robust detection and fallback logic is essential. Research confidence is HIGH for QuickSync/VAAPI integration and HLS buffering (well-documented with official guides), MEDIUM for pychromecast callback timing (version-specific quirks documented in GitHub issues), and HIGH for process cleanup patterns (standard Python asyncio practices).

## Key Findings

### Recommended Stack

v2.0 enhances the validated v1.1 stack (Python 3.11, FastAPI, Playwright, FFmpeg, pychromecast 14.0.9) with four new components: Intel QuickSync hardware acceleration via h264_qsv encoder and VA-API libraries, psutil 7.2.1+ for process lifecycle monitoring, pychromecast MediaStatusListener callbacks for device-initiated stop detection, and optimized HLS configuration with larger buffer windows and deletion thresholds.

**Core technologies (new for v2.0):**
- **h264_qsv (FFmpeg QuickSync encoder)** — 80-90% CPU reduction per stream vs libx264, enables multi-stream scaling. Requires /dev/dri passthrough, Intel 4th gen+ CPU, intel-media-va-driver package.
- **psutil 7.2.1+** — Process tree tracking and graceful termination. Provides children() enumeration, wait_procs() timeout handling, and cross-platform process status monitoring.
- **pychromecast MediaStatusListener** — Event-driven Cast session monitoring. Detects IDLE player state transitions when user stops from TV remote, enables automatic FFmpeg cleanup.
- **HLS buffer optimization** — Increase hls_list_size from 10 to 20 (40s buffer), add hls_delete_threshold=5 to prevent premature segment deletion, and add omit_endlist flag for continuous streaming.

**Critical version requirements:**
- FFmpeg 7.0+ with OneVPL support for 11th gen+ Intel CPUs (or FFmpeg 6.x with Intel Media SDK for older generations)
- intel-media-va-driver 24.x+ for QuickSync codec support
- Proxmox host with IOMMU enabled (intel_iommu=on in GRUB) for GPU passthrough

**What NOT to use:**
- h264_vaapi alone (less efficient than QSV on Gen 12+ hardware)
- `-qsv_device /dev/dri/renderD128` initialization pattern (causes "Invalid argument" errors)
- HLS without omit_endlist flag (Cast device interprets playlist as complete/VOD)
- Misaligned GOP and hls_time values (segments can't be cut mid-GOP, causes freeze)
- process.terminate() without timeout and escalation (may hang indefinitely)

### Expected Features

Research reveals production HLS streaming requires specific table-stakes features that users expect but aren't obvious from basic streaming tutorials. v2.0 feature prioritization follows P0 (blocking production) → P1 (required for production-ready) → P2 (improves experience) → P3 (future enhancement).

**Must have (table stakes - P0/P1):**
- HLS streams play indefinitely without freezing — current 6-second freeze blocks production use
- Automatic FFmpeg cleanup when cast stops from device — orphaned processes lock up VM
- Cast session state monitoring — detect when user stops from TV remote, not just webhook
- Hardware encoder fallback — gracefully use software if QuickSync unavailable for portability
- Configurable HLS buffer settings — tune segment duration, playlist size for network conditions
- Stream validation before casting — prevent 404s or malformed streams

**Should have (competitive - P1/P2):**
- Intel QuickSync hardware acceleration — 5-10x encoding performance, enables multi-stream
- Per-stream resource monitoring — track CPU/memory/GPU to prevent exhaustion before lockup
- Stream health checks — detect FFmpeg hangs before user notices frozen stream
- Configurable encoder presets — balance quality vs performance for different use cases

**Defer (v3+):**
- Adaptive segment duration — adjust based on network conditions, complex with unclear ROI
- Multi-stream orchestration — concurrent streams without contention, architecture supports but defer implementation
- Crash recovery with exponential backoff — automatic FFmpeg restart on transient failures

**Anti-features (avoid):**
- Very short HLS segments <1s — massive overhead, playlist thrashing
- Blocking subprocess calls in async code — kills concurrency
- Global FFmpeg process pool — state leakage, complex lifecycle
- Custom Cast receiver — maintenance burden, $5 fee, 15min propagation delay

### Architecture Approach

v2.0 maintains the validated v1.1 component architecture (FastAPI → StreamTracker → StreamManager → component context managers) and adds three integration points: FFmpegEncoder hardware encoder selection, CastSessionManager session state monitoring, and new ProcessTracker service in orchestration layer for centralized PID tracking.

**Major components (modified):**
1. **FFmpegEncoder** — Add encoder selection logic (h264_qsv vs libx264) with hardware device initialization and fallback path. New `use_hw_accel` parameter triggers QuickSync detection via /dev/dri check and `ffmpeg -encoders | grep qsv`. Single code path with conditional encoder args preserves backward compatibility.
2. **CastSessionManager** — Register MediaStatusListener for player state changes, detect IDLE transitions, trigger cleanup callback. New `on_device_stop` optional callback maintains backward compatibility while enabling device-initiated cleanup.
3. **HLS segment configuration** — Increase hls_list_size to 20, add hls_delete_threshold=5, add omit_endlist flag. Root cause of 6-second freeze: insufficient buffer window + aggressive segment deletion causes Cast device buffer underrun.

**Major components (new):**
1. **ProcessTracker** — Centralized registry of FFmpeg PIDs with lifecycle management. Provides register_process(), cleanup_session(), cleanup_all() methods. Enables signal handling for Docker SIGTERM, tracks processes independently of asyncio task lifecycle, implements timeout escalation (stdin 'q' → SIGTERM → SIGKILL).
2. **MediaStatusListener** — Implements pychromecast callback protocol. Monitors new_media_status() for playerState changes, detects PLAYING → IDLE transitions indicating device stop, uses asyncio.create_task() to bridge sync callback to async cleanup.

**Critical architecture patterns:**
- **Graceful degradation** — QuickSync detection with software fallback ensures portability
- **Observer pattern** — MediaStatusListener decouples Cast state changes from cleanup logic
- **Registry pattern** — ProcessTracker provides single source of truth for active processes
- **Timeout escalation** — Progressive termination (graceful → terminate → kill) maximizes data integrity while guaranteeing cleanup

**Phase ordering rationale:**
Research reveals clear dependency chain: HLS buffering fix is independent (config-only change), fMP4 validation confirms dual-mode architecture, session state monitoring provides foundation for process cleanup, process tracking enables safe hardware acceleration (can forcibly cleanup hung processes). Each phase builds on previous validation.

### Critical Pitfalls

Research identified 7 critical pitfalls that will cause production failures if not properly addressed. Top 3 are blockers for v2.0, remaining 4 require careful implementation to avoid.

1. **HLS Segment Duration vs Buffer Window Mismatch (CRITICAL)** — Stream freezes at exactly 6 seconds because Cast device expects minimum buffer of 3 segments before playback. Current hls_time=2 with hls_list_size=10 provides 20s buffer which should work, but missing omit_endlist flag and aggressive deletion cause premature segment unavailability. Fix: increase hls_list_size to 20 (40s buffer), add hls_delete_threshold=5, add omit_endlist flag. Warning signs: stream plays for N seconds then freezes, FFmpeg continues encoding but Cast stops requesting segments.

2. **FFmpeg Process Cleanup Race Conditions (CRITICAL)** — Multiple orphaned FFmpeg processes accumulate until VM locks up. Race conditions occur when: encoding mid-frame (takes >5s to flush), x11grab source disappears before FFmpeg (causes segfault per FFmpeg bug #7312), segment write mid-operation (file lock prevents cleanup), child processes don't receive termination signals. Fix: send 'q' to stdin first (graceful stop), verify context manager nesting (FFmpeg before Xvfb), use process groups (os.setsid), track all PIDs globally, reduce kill timeout to 3s. Warning signs: multiple ffmpeg processes when only one stream active, defunct zombies, VM unresponsive after start/stop cycles.

3. **Intel QuickSync Driver and Permission Configuration (CRITICAL)** — Hardware acceleration fails with "unsupported (-3)" or "Permission denied" errors, FFmpeg silently falls back to software encoding. Multiple layers must align: i915 kernel module loaded, correct VAAPI driver installed (intel-media-va-driver for Gen 8+ vs i965-va-driver for older), Docker render group GID matches host, FFmpeg built with QSV support, Proxmox GPU passed through. Fix: verify CPU generation (4th gen+ required), install correct driver for generation, match Docker GID to host `getent group render`, explicitly set LIBVA_DRIVER_NAME=iHD or i965, add fallback detection. Warning signs: CPU at 100% despite attempting hardware, vainfo fails, /dev/dri missing, "MFX session" errors.

4. **Proxmox GPU Passthrough IOMMU Configuration** — iGPU not accessible in VM even after passthrough configured. Requires: VT-d enabled in BIOS, intel_iommu=on in GRUB, iGPU has own IOMMU group, GPU added to VM in Proxmox UI, drivers installed in VM. Fix: enable VT-d in BIOS, edit /etc/default/grub with intel_iommu=on iommu=pt, run update-grub and reboot host, verify with `dmesg | grep IOMMU`, add PCI device 00:02.0 to VM, install intel-media-va-driver in VM, verify /dev/dri exists. Warning signs: Proxmox shows GPU but VM doesn't, dmesg shows no IOMMU, /dev/dri missing in VM.

5. **pychromecast Callback Timing and Device Stop Detection** — User stops cast from TV remote but application doesn't detect it, FFmpeg continues encoding indefinitely. Current implementation doesn't register status listeners, so DISCONNECTED events and IDLE state transitions are missed. Fix: register MediaStatusListener for new_media_status() callbacks, detect PLAYING → IDLE transition, use asyncio.Event for stop signaling, handle callbacks thread-safe with loop.call_soon_threadsafe(), add 10s grace period for temporary network blips. Warning signs: stopping from remote doesn't terminate stream, orphaned FFmpeg accumulates, CPU high when TV shows "Ready to cast".

**Technical debt to avoid:**
- Using libx264 in production (100% CPU, can't scale)
- Ignoring segment cleanup failures (disk fills, system crashes)
- Hardcoding render group GID (breaks on other hosts)
- Skipping IOMMU configuration (hardware acceleration never works)
- Not implementing process group termination (zombie processes)

## Implications for Roadmap

Based on research findings and dependency analysis, v2.0 should follow 5-phase structure with risk escalation pattern: start with low-risk config changes, validate existing features, add monitoring foundations, implement robust cleanup, finally integrate hardware acceleration.

### Phase 1: HLS Buffering Fix
**Rationale:** Minimal code change (FFmpegEncoder configuration), solves known production blocker (6-second freeze), no new dependencies, immediately testable. Research shows this is configuration issue, not architectural problem.

**Delivers:** HLS streams play indefinitely without freezing, proper segment buffering for Cast devices, continuous streaming support.

**Addresses:**
- Fix 6-second freeze (P0 feature from FEATURES.md)
- HLS segment duration vs buffer window mismatch (Pitfall #1 from PITFALLS.md)
- HLS delete_segments flag failures (Pitfall #6 from PITFALLS.md)

**Avoids:** Buffer underruns from premature segment deletion, disk filling from orphaned segments.

### Phase 2: fMP4 Low-Latency Validation
**Rationale:** Already implemented in v1.1, only needs validation testing. Confirms dual-mode architecture works, provides low-latency alternative to HLS. Independent of other v2.0 features.

**Delivers:** Validated fMP4 CMAF-compliant fragmented MP4 streaming, <2s latency mode confirmed working, documented movflags configuration rationale.

**Addresses:**
- fMP4 low-latency mode validation (P1 feature from FEATURES.md)
- fMP4 fragmentation flags for Cast compatibility (Pitfall #7 from PITFALLS.md)

**Avoids:** Shipping feature without validation, discovering Cast incompatibility in production.

### Phase 3: Cast Session State Monitoring
**Rationale:** Provides foundation for automatic cleanup, prerequisite for process lifecycle management. Medium complexity (new listener pattern), independently testable by stopping from TV remote.

**Delivers:** Device-initiated stop detection, MediaStatusListener implementation, automatic cleanup callback infrastructure.

**Addresses:**
- Cast session state monitoring (P0 feature from FEATURES.md)
- pychromecast callback timing and device stop detection (Pitfall #5 from PITFALLS.md)

**Avoids:** Orphaned FFmpeg processes when user stops from device, wasted CPU resources, VM lockup from accumulating processes.

### Phase 4: Process Lifecycle Management
**Rationale:** Depends on session state monitoring (Phase 3), implements robust cleanup for production stability. Complex (signal handling, process groups), critical for preventing VM lockup.

**Delivers:** ProcessTracker registry service, signal handlers for Docker SIGTERM, timeout-based cleanup escalation, orphaned process prevention, graceful shutdown support.

**Addresses:**
- FFmpeg auto-cleanup when cast stops (P0 feature from FEATURES.md)
- FFmpeg process cleanup race conditions (Pitfall #2 from PITFALLS.md)

**Avoids:** VM lockup from orphaned processes, zombie FFmpeg accumulation, crashes from Xvfb/FFmpeg ordering issues.

### Phase 5: Intel QuickSync Hardware Acceleration
**Rationale:** Most complex (hardware detection, driver config, fallback logic), requires Proxmox setup, optional feature (software encoding still works). Depends on stable process lifecycle (Phase 4) to handle hung hardware encoders.

**Delivers:** h264_qsv encoder integration, QuickSync detection and initialization, graceful fallback to software encoding, Proxmox GPU passthrough documentation, 80-90% CPU reduction per stream.

**Addresses:**
- Intel QuickSync hardware acceleration (P1 feature from FEATURES.md)
- Hardware encoder fallback (P1 feature from FEATURES.md)
- QuickSync driver and permission configuration (Pitfall #3 from PITFALLS.md)
- Proxmox GPU passthrough IOMMU configuration (Pitfall #4 from PITFALLS.md)

**Avoids:** Silent fallback to software encoding, Docker permission failures, Proxmox GPU not accessible in VM, driver mismatches between Intel generations.

### Phase Ordering Rationale

**Risk escalation approach:**
1. Phase 1 (LOW risk): Config change only, no new code paths
2. Phase 2 (LOW risk): Validation testing, no code changes
3. Phase 3 (MEDIUM risk): New callback pattern, standard pychromecast usage
4. Phase 4 (HIGH risk): Signal handling and process groups, complex but well-documented
5. Phase 5 (HIGH risk): Hardware integration with fallback, optional feature

**Value delivery pattern:**
- Phase 1 fixes production blocker immediately
- Phase 2 validates existing feature claims
- Phase 3 enables resource management foundation
- Phase 4 prevents VM lockup (critical for production)
- Phase 5 enables scaling (nice-to-have performance)

**Dependency chain:**
- Phases 1-2 are independent
- Phase 3 provides callback mechanism for Phase 4
- Phase 4 cleanup stability required before Phase 5 hardware complexity
- Each phase independently deployable (can ship 1-3 without 4-5)

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 5 (QuickSync):** Proxmox-specific GPU passthrough configuration may need experimentation on actual hardware. IOMMU group conflicts and driver selection (iHD vs i965) vary by CPU generation. Plan for testing iteration on Proxmox setup.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (HLS):** Well-documented FFmpeg HLS parameters, industry best practices established
- **Phase 2 (fMP4):** CMAF specification clear, current implementation already correct
- **Phase 3 (Session Monitoring):** pychromecast MediaStatusListener standard usage, examples available
- **Phase 4 (Process Lifecycle):** Python asyncio subprocess patterns well-established, psutil library mature

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Intel QuickSync integration heavily documented (Jellyfin, Frigate guides), HLS configuration industry-standard, psutil mature library, pychromecast 14.0.9 stable |
| Features | HIGH | Production HLS streaming requirements well-established, Cast device behavior documented, hardware acceleration value clear from benchmarks |
| Architecture | HIGH | Component modifications minimal (parameter additions), patterns proven (graceful degradation, observer, registry, timeout escalation), existing v1.1 architecture validated |
| Pitfalls | HIGH | QuickSync driver issues extensively documented (PhotoPrism, Immich GitHub issues), HLS buffering best practices established, FFmpeg process cleanup patterns well-known, x11grab crash documented (FFmpeg bug #7312) |

**Overall confidence:** HIGH

All v2.0 features build on mature technologies with extensive real-world usage documentation. Intel QuickSync has comprehensive guides from Jellyfin (official hardware acceleration docs), Frigate (community discussions comparing VAAPI vs QSV), and Perfect Media Server (Proxmox passthrough specifics). HLS configuration derives from Wowza best practices and video.js project experiences. Process lifecycle management follows standard Python asyncio patterns. pychromecast status listeners are used extensively in Home Assistant (production code examples available).

### Gaps to Address

**Proxmox GPU passthrough host-specific variations:** IOMMU group conflicts depend on motherboard/BIOS. Some systems may have iGPU sharing IOMMU group with other critical devices, preventing passthrough. Mitigation: provide Proxmox-specific troubleshooting guide, verify IOMMU groups during implementation, document alternative approaches (LXC device mapping vs VM passthrough).

**pychromecast callback thread safety:** MediaStatusListener callbacks execute in pychromecast's internal thread, not asyncio event loop. Current research shows asyncio.create_task() usage, but some GitHub issues mention loop.call_soon_threadsafe() as safer approach. Mitigation: test both patterns during Phase 3 implementation, verify no race conditions with asyncio.Event usage.

**Intel driver selection automation (iHD vs i965):** CPU generation detection to auto-select correct VAAPI driver not implemented in research. Manual LIBVA_DRIVER_NAME setting required. Mitigation: provide clear documentation on which driver for which CPU generation, add health check to validate driver loads correctly, implement detection logic during Phase 5 if time permits.

**HLS segment deletion timing under load:** Research shows delete_segments failures under file locking, but testing needed to confirm behavior with aiohttp concurrent serving + FFmpeg deletion. Mitigation: Phase 1 adds hls_delete_threshold=5 for safety margin, implement background cleanup task as fallback, monitor /tmp/streams/ disk usage in health checks.

**Cast device MIME type requirements for fMP4:** Research suggests Content-Type: video/mp4 required, but aiohttp FileResponse behavior needs verification. Mitigation: Phase 2 validation testing includes server response header verification, test with actual Cast device (not just browser).

## Sources

### Primary (HIGH confidence)

**Intel QuickSync / Hardware Acceleration:**
- [Jellyfin: HWA Tutorial On Intel GPU](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/intel/) — Official hardware acceleration guide with QSV configuration
- [Medium: Hardware-accelerate video transcoding via Quicksync](https://medium.com/@yllanos/how-to-hardware-accelerate-video-transcoding-via-quicksync-qsv-while-retaining-hdr-using-linux-afe25780718c) — Docker + QSV complete setup guide
- [Intel: Cloud Computing QuickSync Video FFmpeg White Paper](https://www.intel.com/content/dam/www/public/us/en/documents/white-papers/cloud-computing-quicksync-video-ffmpeg-white-paper.pdf) — Official Intel QSV reference
- [Hardware video acceleration - ArchWiki](https://wiki.archlinux.org/title/Hardware_video_acceleration) — Comprehensive VAAPI/QSV Linux guide

**HLS Streaming:**
- [Wowza: HLS Latency Sucks, But Here's How to Fix It](https://www.wowza.com/blog/hls-latency-sucks-but-heres-how-to-fix-it) — Industry best practices for HLS configuration
- [Bitmovin: MPEG-DASH & HLS segment length](https://bitmovin.com/mpeg-dash-hls-segment-length/) — Segment duration analysis
- [OTTVerse: HLS Packaging using FFmpeg Tutorial](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/) — Complete FFmpeg HLS configuration guide
- [Streaming Learning Center: Choosing Segment Duration](https://streaminglearningcenter.com/learning/choosing-the-optimal-segment-duration.html) — Production recommendations

**Proxmox GPU Passthrough:**
- [Proxmox Forum: Jellyfin + QSV + unprivileged LXC](https://forum.proxmox.com/threads/guide-jellyfin-remote-network-shares-hw-transcoding-with-intels-qsv-unprivileged-lxc.142639/) — Complete LXC passthrough guide
- [Perfect Media Server: Quick Sync and iGPU passthrough](https://perfectmediaserver.com/05-advanced/passthrough-igpu-gvtg/) — Proxmox-specific configuration
- [Jack Cuthbert: Intel NUC GPU passthrough in Proxmox 6.1](https://jackcuthbert.dev/blog/intel-nuc-gpu-passthrough-in-proxmox-plex-docker) — Working implementation guide

**pychromecast:**
- [pychromecast GitHub: media.py](https://github.com/home-assistant-libs/pychromecast/blob/master/pychromecast/controllers/media.py) — MediaStatusListener source code
- [pychromecast PyPI](https://pypi.org/project/PyChromecast/) — Version 14.0.9 documentation
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) — Official asyncio process management

**Process Management:**
- [psutil PyPI](https://pypi.org/project/psutil/) — Version 7.2.1 package documentation
- [psutil Documentation](https://psutil.readthedocs.io/) — Complete API reference

### Secondary (MEDIUM confidence)

**HLS Implementation:**
- [video.js Issue #6366](https://github.com/videojs/video.js/issues/6366) — HLS + fMP4 lag reduction discussion
- [Martin Riedl: FFmpeg as HLS streaming server Part 2](https://www.martin-riedl.de/2018/08/24/using-ffmpeg-as-a-hls-streaming-server-part-2/) — Segmentation best practices
- [hls.js Issue #1626](https://github.com/video-dev/hls.js/issues/1626) — Stream freezing troubleshooting

**QuickSync Configuration:**
- [Gough's Tech Zone: h264_qsv Codec Round-Up 2023](https://goughlui.com/2023/12/28/video-codec-round-up-2023-part-6-h264_qsv-h-264-intel-quick-sync-video/) — Quality and settings analysis
- [Nelson's Log: hevc_qsv Intel Quick Sync settings](https://nelsonslog.wordpress.com/2022/08/22/ffmpeg-and-hevc_qsv-intel-quick-sync-settings/) — QSV encoder parameters
- [Frigate Discussion #6405](https://github.com/blakeblackshear/frigate/discussions/6405) — VAAPI vs QSV comparison

**pychromecast Callbacks:**
- [pychromecast Issue #84](https://github.com/balloob/pychromecast/issues/84) — Detecting when app stops casting
- [pychromecast Issue #560](https://github.com/home-assistant-libs/pychromecast/issues/560) — Runtime error documentation
- [Home Assistant Issue #35780](https://github.com/home-assistant/core/issues/35780) — Media status callback exceptions

**FFmpeg Process Cleanup:**
- [FFmpeg Trac #7312](https://trac.ffmpeg.org/ticket/7312) — x11grab crash when source disappears
- [imageio-ffmpeg Issue #13](https://github.com/imageio/imageio-ffmpeg/issues/13) — Process termination race conditions
- [Raspberry Pi Forums: Gently terminate ffmpeg](https://forums.raspberrypi.com/viewtopic.php?t=284030) — Graceful termination patterns

**Docker /dev/dri Permissions:**
- [PhotoPrism Issue #2739](https://github.com/photoprism/photoprism/issues/2739) — Render group GID mismatch
- [Immich Discussion #13563](https://github.com/immich-app/immich/discussions/13563) — /dev/dri/renderD128 access failures
- [linuxserver/docker-plex Issue #211](https://github.com/linuxserver/docker-plex/issues/211) — Render group permissions

### Research Document Cross-References
- Full stack details: `.planning/research/STACK.md`
- Complete feature analysis: `.planning/research/FEATURES.md`
- Architecture patterns: `.planning/research/ARCHITECTURE.md`
- Detailed pitfalls: `.planning/research/PITFALLS.md`

---
*Research completed: 2026-01-18*
*Ready for roadmap: YES*
*Milestone: v2.0 Stability and Hardware Acceleration*
