# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-18)

**Core value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.
**Current focus:** v2.0 Stability and Hardware Acceleration - Phase 10: Intel QuickSync Hardware Acceleration

## Current Position

Phase: 10 of 13 (Intel QuickSync Hardware Acceleration)
Plan: 3 of ? in phase
Status: In progress
Last activity: 2026-01-19 — Completed 10-03-PLAN.md (Encoder Integration)

Progress: [█████████░░░░░░░░░░░] 50% (24/? plans complete across all phases)

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
- Total plans completed: 4
- Average duration: 7.0 min
- Total execution time: ~30 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.0 (1-4) | 12 | ~78 min | 6.5 min |
| v1.1 (5-8) | 8 | ~43 min | 5.4 min |
| v2.0 (9-13) | 4 | ~30 min | 7.5 min |

**Recent Trend:**
- Phase 9 complete: 2 plans, 18 min total (15 min + 3 min)
- Phase 10 in progress: 2 plans complete, 12 min (10-01: 7 min, 10-03: 5 min)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v2.0 work:

- v2.0 Phase 10-03: self.encoder instance variable pattern - encoder name stored in __init__ for cross-method access between build_ffmpeg_args() and __aenter__() logging
- v2.0 Phase 10-03: ICQ mode (global_quality) for h264_qsv - QuickSync uses global_quality=23 with look_ahead instead of bitrate/preset (they conflict)
- v2.0 Phase 10-03: Empty encoder_args for libx264 fallback - reuses existing preset/bitrate config from encoder.py, avoids duplication
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

3 todos pending. See `.planning/todos/pending/`

- **Direct RTSP to Cast streaming** — bypass browser capture for camera feeds (video)
- **Hardware acceleration (QuickSync/VAAPI)** — reduce CPU usage for FFmpeg encoding (v2.0 Phase 13)
- **FFmpeg process cleanup bug** — multiple FFmpeg processes spawned, not cleaned up on error (v2.0 Phase 12)

### Resolved Todos

- **FFmpeg subprocess logging** — ✅ RESOLVED in Phase 9 (GAP-09-01: FFmpeg stdout/stderr now forwarded to application logs with level-based classification)
- **HLS stream buffering issue** — ✅ RESOLVED in Phase 9 (HLS buffer window increased to 40s, segment retention added, continuous streaming signal implemented)

### Blockers/Concerns

**v2.0 addresses these known issues:**
- Orphaned FFmpeg processes (Phase 12 target)
- CPU-bound software encoding (Phase 13 target)

**Resolved in v2.0:**
- ✅ FFmpeg diagnostic gap (Phase 9 - GAP-09-01 closed, subprocess logging now captured)
- ✅ HLS 6-second freeze bug (Phase 9 - buffer window and segment retention fixed)

**Resolved in previous milestones:**
- Cast device 404 errors (Phase 8 - IP address fixed)
- WSL2 mDNS limitation (v1.0 - static IP workaround documented)

## Session Continuity

Last session: 2026-01-19 (Phase 10-03 complete: Encoder Integration)
Stopped at: Completed 10-03-PLAN.md execution
Resume with: Continue Phase 10 planning/execution (next plan: 10-04 Testing)
Resume file: None

### Context for Next Session
- Phase 10-03 complete: FFmpeg encoder integration with hardware acceleration
  - FFmpegEncoder imports and uses HardwareAcceleration class
  - Encoder dynamically selects h264_qsv or libx264 based on hardware availability
  - Conditional rate control: ICQ mode (global_quality) for QSV, bitrate/preset for libx264
  - Health endpoint reports hardware acceleration status (quicksync_available, encoder)
  - Encoder name logged in startup messages for debugging
- Phase 10-02 complete: Hardware detection module (10-02-SUMMARY.md not created but code committed)
  - HardwareAcceleration class with runtime QuickSync detection
  - Graceful fallback to software encoding when hardware unavailable
- Phase 10-01 complete: Docker infrastructure configured for Intel QuickSync
  - FFmpeg 7.1.3 with h264_qsv encoder verified in container
  - Intel iHD VAAPI drivers installed
  - GPU device passthrough configured (/dev/dri)
- **User action required before testing:**
  - Run scripts/detect-gpu-gids.sh to get render and video GIDs
  - Replace placeholder values in docker-compose.yml group_add section
  - Verify /dev/dri device exists on host system
  - Confirm Intel GPU with QuickSync support available (lspci | grep -i vga)
- **Next steps for Phase 10:**
  - Plan 10-04: Test hardware acceleration with actual GPU, verify performance improvement
  - Verify software fallback works correctly
  - Check health endpoint reports correct encoder status
- **Technical notes:**
  - ICQ mode quality target: global_quality=23 (similar to CRF)
  - Look-ahead enabled for h264_qsv: 40-frame depth
  - libx264 fallback uses existing preset/bitrate config from encoder.py

---
*State updated: 2026-01-19 after Phase 9 complete and roadmap reordering*
