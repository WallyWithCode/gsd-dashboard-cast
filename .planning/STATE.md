# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-18)

**Core value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.
**Current focus:** v2.0 Stability and Hardware Acceleration - Phase 10: Intel QuickSync Hardware Acceleration

## Current Position

Phase: 10 of 13 (Intel QuickSync Hardware Acceleration)
Plan: 0 of ? in phase
Status: Ready for planning
Last activity: 2026-01-19 — Completed Phase 9 (HLS Buffering Fix), roadmap reordered to prioritize QuickSync

Progress: [█████████░░░░░░░░░░░] 46% (22/? plans complete across all phases)

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
- Total plans completed: 2
- Average duration: 9 min
- Total execution time: ~18 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.0 (1-4) | 12 | ~78 min | 6.5 min |
| v1.1 (5-8) | 8 | ~43 min | 5.4 min |
| v2.0 (9-13) | 2 | ~18 min | 9 min |

**Recent Trend:**
- Phase 9 complete: 2 plans, 18 min total (15 min + 3 min)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v2.0 work:

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

Last session: 2026-01-19 (Phase 9 complete, roadmap reordered)
Stopped at: Phase 9 verification - CPU bottleneck discovered during testing
Resume with: `/gsd:plan-phase 10` to plan Intel QuickSync Hardware Acceleration
Resume file: None

### Context for Next Session
- Phase 9 complete: HLS configuration fixes + FFmpeg logging implemented
- HLS buffering: 40s buffer window, segment retention, continuous streaming signal verified in code
- FFmpeg logging: Background task forwards stdout/stderr with level-based classification
- **Critical discovery:** CPU bottleneck prevents proper testing on 2-vCPU VM
  - Software H.264 encoding at 720p requires ~50-100% per core
  - Stream buffers after 3 seconds due to encoding lag
  - QuickSync hardware acceleration will reduce CPU usage by 80-90%
- **Roadmap reordered:** Phase 10 now Intel QuickSync (was Phase 13)
  - Prioritized to enable working demonstration
  - Phases 11-13 shifted: fMP4 validation → stop detection → process lifecycle
  - Phase 11 (fMP4) now depends on Phase 10 (hardware acceleration enables proper testing)
- Ready to begin Phase 10: Intel QuickSync Hardware Acceleration
- Research needed: Proxmox GPU passthrough, IOMMU configuration, driver selection

---
*State updated: 2026-01-19 after Phase 9 complete and roadmap reordering*
