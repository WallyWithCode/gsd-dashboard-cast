# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-18)

**Core value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.
**Current focus:** v2.0 Stability and Hardware Acceleration - Phase 9: HLS Buffering Fix

## Current Position

Phase: 9 of 13 (HLS Buffering Fix)
Plan: Not yet planned
Status: Ready to plan
Last activity: 2026-01-18 — v2.0 roadmap created

Progress: [████████░░░░░░░░░░░░] 40% (20/? plans complete across all phases)

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
- Total plans completed: 0
- Average duration: TBD
- Total execution time: TBD

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.0 (1-4) | 12 | ~78 min | 6.5 min |
| v1.1 (5-8) | 8 | ~43 min | 5.4 min |
| v2.0 (9-13) | 0 | - | - |

**Recent Trend:**
- v2.0 just started — no trend data yet

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v2.0 work:

- v1.1: aiohttp over FastAPI StaticFiles — Independent server on configurable port (enables 8000/8080 separation)
- v1.1: fMP4 movflags: frag_keyframe+empty_moov+default_base_moof — Streaming-friendly fragmentation
- v1.1: Default mode 'hls' — Backward compatibility with existing webhooks
- v1.0: Software encoding for v1 — Hardware acceleration deferred to v2.0 (QuickSync/VAAPI integration)

### Pending Todos

4 todos pending. See `.planning/todos/pending/`

- **Direct RTSP to Cast streaming** — bypass browser capture for camera feeds (video)
- **Hardware acceleration (QuickSync/VAAPI)** — reduce CPU usage for FFmpeg encoding (v2.0 Phase 13)
- **FFmpeg process cleanup bug** — multiple FFmpeg processes spawned, not cleaned up on error (v2.0 Phase 12)
- **HLS stream buffering issue** — stream freezes after 6 seconds, needs HLS segment/timeout tuning (v2.0 Phase 9)

### Blockers/Concerns

**v2.0 addresses these known issues:**
- HLS 6-second freeze bug (Phase 9 target)
- Orphaned FFmpeg processes (Phase 12 target)
- CPU-bound software encoding (Phase 13 target)

**Resolved in previous milestones:**
- Cast device 404 errors (Phase 8 - IP address fixed)
- WSL2 mDNS limitation (v1.0 - static IP workaround documented)

## Session Continuity

Last session: 2026-01-18 (v2.0 roadmap creation)
Stopped at: v2.0 roadmap and state initialization complete
Resume with: `/gsd:plan-phase 9` to plan HLS Buffering Fix
Resume file: None

### Context for Next Session
- v2.0 roadmap created with 5 phases (9-13)
- Phase 9 addresses HLS 6-second freeze (config-only fix)
- Phase 10 validates fMP4 low-latency mode (existing feature)
- Phase 11 adds device-initiated stop detection (foundation for cleanup)
- Phase 12 implements robust process lifecycle management (fixes FFmpeg leak)
- Phase 13 integrates Intel QuickSync hardware acceleration (80-90% CPU reduction)
- Ready to begin planning Phase 9: HLS Buffering Fix

---
*State updated: 2026-01-18 after v2.0 roadmap creation*
