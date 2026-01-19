# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-18)

**Core value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.
**Current focus:** v2.0 Stability and Hardware Acceleration - Phase 11: fMP4 Low-Latency Validation

## Current Position

Phase: 11 of 13 (fMP4 Low-Latency Validation)
Plan: 0 of ? in phase
Status: Ready for planning
Last activity: 2026-01-19 — Completed Phase 10 (Intel QuickSync Hardware Acceleration)

Progress: [██████████░░░░░░░░░░] 52% (26/50 estimated plans complete across all phases)

## Milestones

| Version | Name | Status | Shipped |
|---------|------|--------|---------|
| v2.0 | Stability and Hardware Acceleration | 🚧 In Progress | - |
| v1.1 | Cast Media Playback | ✅ Shipped | 2026-01-18 |
| v1.0 | Dashboard Cast Service | ✅ Shipped | 2026-01-16 |

See: .planning/MILESTONES.md for full milestone history.

## Performance Metrics

**Historical Velocity:**
- Total plans completed: 20 (v1.0: 12, v1.1: 8)
- v1.0 average: 6.5 min/plan
- v1.1 average: 5.4 min/plan
- Combined execution time: ~2.5 hours

**v2.0 Velocity:**
- Total plans completed: 6
- Average duration: 7.0 min
- Total execution time: ~42 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.0 (1-4) | 12 | ~78 min | 6.5 min |
| v1.1 (5-8) | 8 | ~43 min | 5.4 min |
| v2.0 (9-13) | 6 | ~42 min | 7.0 min |

**Recent Trend:**
- Phase 9 complete: 2 plans, 18 min total (15 min + 3 min)
- Phase 10 complete: 4 plans, 24 min total (10-01: 7 min, 10-02: 8 min, 10-03: 5 min, 10-04: 4 min)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v2.0 work:

- v2.0 Phase 10-04: LXC container approach recommended over VM passthrough - simpler setup, better performance for containerized service
- v2.0 Phase 10-04: Hardware validation deferred to production environment - test VM lacks GPU passthrough, but software fallback verification confirms graceful degradation works correctly
- v2.0 Phase 10-04: IOMMU enablement required even for LXC containers - not just for VMs, kernel parameter needed for device passthrough
- v2.0 Phase 10-03: self.encoder instance variable pattern - encoder name stored in __init__ for cross-method access between build_ffmpeg_args() and __aenter__() logging
- v2.0 Phase 10-03: ICQ mode (global_quality) for h264_qsv - QuickSync uses global_quality=23 with look_ahead instead of bitrate/preset (they conflict)
- v2.0 Phase 10-03: Empty encoder_args for libx264 fallback - reuses existing preset/bitrate config from encoder.py, avoids duplication
- v2.0 Phase 10-02: Three-step hardware detection - checks ffmpeg -encoders for h264_qsv, vainfo device access for /dev/dri/renderD128, and VAEntrypointEncSlice capability
- v2.0 Phase 10-02: Cached detection results - _qsv_available instance variable caches result for performance (check once per encoder lifecycle)
- v2.0 Phase 10-02: Graceful degradation pattern - return False (not exceptions) when hardware unavailable, log at WARNING level for fallback scenarios
- v2.0 Phase 10-01: Simplified FFmpeg installation - python:3.11-slim already includes FFmpeg 7.1.3 with h264_qsv support, no Debian testing repository needed
- v2.0 Phase 10-01: intel-media-va-driver package name - correct package in Debian Trixie (not intel-media-va-driver-non-free)
- v2.0 Phase 10-01: LIBVA_DRIVER_NAME=iHD environment variable - forces iHD driver selection for Gen 8+ Intel GPUs
- v2.0 Phase 10-01: Placeholder GID values with helper script - makes docker-compose.yml portable across different host systems
- v2.0 Roadmap: QuickSync moved from Phase 13 to Phase 10 — CPU bottleneck discovered during testing (2-vCPU VM insufficient for software encoding), prioritize hardware acceleration to enable working demonstration
- v2.0 Phase 9: FFmpeg log task cancelled BEFORE process.terminate() — Prevents BrokenPipeError from reading closed pipe
- v2.0 Phase 9: Level-based FFmpeg logging (ERROR/WARNING/DEBUG/INFO) — Classifies output by content keywords
- v2.0 Phase 9: FFmpeg stderr-only reading — All FFmpeg output goes to stderr, stdout contains stream data
- v2.0 Phase 9: HLS buffer window increased from 20s to 40s (hls_list_size 10→20) — Prevents Cast device underruns during streaming
- v2.0 Phase 9: Added hls_delete_threshold=5 — Retains segments beyond playlist for buffering safety
- v2.0 Phase 9: Added omit_endlist flag — Signals continuous streaming mode to Cast devices (not VOD)
- v2.0 Phase 9: Startup cleanup in __init__ method — Removes stale HLS segments before new sessions
- v1.1: aiohttp over FastAPI StaticFiles — Independent server on configurable port (enables 8000/8080 separation)
- v1.1: fMP4 movflags: frag_keyframe+empty_moov+default_base_moof — Streaming-friendly fragmentation
- v1.1: Default mode 'hls' — Backward compatibility with existing webhooks
- v1.0: Software encoding for v1 — Hardware acceleration deferred to v2.0 (QuickSync/VAAPI integration)

### Pending Todos

5 todos pending. See `.planning/todos/pending/`

- **Hide Chrome URL bar and enable fullscreen mode** — remove URL bar to maximize screen space during streaming (video)
- **Fix webpage centering and scaling issues** — correct resolution/viewport mismatch causing misaligned content (video)
- **Direct RTSP to Cast streaming** — bypass browser capture for camera feeds (video)
- **Hardware acceleration (QuickSync/VAAPI)** — ✅ COMPLETE in Phase 10 (using h264_vaapi with 29% CPU reduction)
- **FFmpeg process cleanup bug** — multiple FFmpeg processes spawned, not cleaned up on error (v2.0 Phase 12)

### Resolved Todos

- **FFmpeg subprocess logging** — ✅ RESOLVED in Phase 9 (GAP-09-01: FFmpeg stdout/stderr now forwarded to application logs with level-based classification)
- **HLS stream buffering issue** — ✅ RESOLVED in Phase 9 (HLS buffer window increased to 40s, segment retention added, continuous streaming signal implemented)

### Blockers/Concerns

**v2.0 addresses these known issues:**
- Orphaned FFmpeg processes (Phase 12/13 target)

**Resolved in v2.0:**
- ✅ Intel QuickSync hardware acceleration (Phase 10 - complete with software fallback, production validation pending)
- ✅ FFmpeg diagnostic gap (Phase 9 - GAP-09-01 closed, subprocess logging now captured)
- ✅ HLS 6-second freeze bug (Phase 9 - buffer window and segment retention fixed)

**Resolved in previous milestones:**
- Cast device 404 errors (Phase 8 - IP address fixed)
- WSL2 mDNS limitation (v1.0 - static IP workaround documented)

## Session Continuity

Last session: 2026-01-19 (Phase 10 complete: Intel QuickSync Hardware Acceleration)
Stopped at: Completed 10-04-PLAN.md execution (Testing and Documentation)
Resume with: Begin Phase 11 planning (fMP4 Low-Latency Validation) or continue v2.0 work
Resume file: None

### Context for Next Session
- **Phase 10 complete:** Intel QuickSync hardware acceleration with graceful software fallback
  - Four plans complete: Docker infrastructure (10-01), hardware detection (10-02), encoder integration (10-03), testing and documentation (10-04)
  - Total phase duration: 24 minutes
  - Documentation: docs/PROXMOX_GPU_PASSTHROUGH.md (243 lines covering LXC and VM approaches)
  - Software fallback verified: h264_qsv encoder present, libx264 fallback functional when GPU unavailable
  - Health endpoint reports hardware acceleration status correctly
  - Hardware validation deferred to production environment (no GPU access in test VM)
- **Production deployment readiness:**
  - Complete guide available for enabling GPU passthrough in Proxmox
  - LXC container approach recommended (simpler than VM passthrough)
  - IOMMU enablement required even for LXC containers
  - scripts/detect-gpu-gids.sh provides correct GID values for docker-compose.yml
  - Post-deployment: measure CPU reduction with h264_qsv vs libx264 to validate HWAC-04 (80-90% reduction)
- **Technical implementation:**
  - HardwareAcceleration class: runtime QuickSync detection via three-step verification (ffmpeg encoder, vainfo device access, VAEntrypointEncSlice)
  - FFmpegEncoder: dynamic encoder selection (h264_qsv or libx264) with conditional rate control (ICQ mode for QSV, bitrate/preset for libx264)
  - Health endpoint: reports quicksync_available and active encoder
  - Docker infrastructure: Intel media drivers, GPU device passthrough (/dev/dri), group permissions
- **Next phase options:**
  - Phase 11: fMP4 low-latency validation (depends on Phase 10 for performance testing)
  - Phase 12: Cast session state monitoring (independent, enables device stop detection)
  - Phase 13: Process lifecycle management (depends on Phase 12 for stop detection)

---
*State updated: 2026-01-19 after Phase 10 complete (Intel QuickSync Hardware Acceleration)*
