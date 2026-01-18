# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-16)

**Core value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.
**Current focus:** v1.1 Cast Media Playback — dual-mode streaming

## Current Position

Phase: 8 of 8 (Cast Media Playback)
Plan: 1 of 1 (Completed)
Status: Phase complete - v1.1 milestone ready
Last activity: 2026-01-18 — Completed 08-01-PLAN.md (Cast Media Playback Implementation)

Progress: ██████████ 100% (v1.1 — 3/3 phases complete)

## Milestones

| Version | Name | Status | Shipped |
|---------|------|--------|---------|
| v1.1 | Cast Media Playback | ✅ Shipped | 2026-01-18 |
| v1.0 | Dashboard Cast Service | ✅ Shipped | 2026-01-16 |

See: .planning/MILESTONES.md for full milestone history.

## Performance Metrics

**v1.1 Velocity:**
- Total plans completed: 15 (v1.0: 12, v1.1: 3)
- Average duration: 5.4 min
- Total execution time: 1.35 hours
- Timeline: 4 days (2026-01-15 → 2026-01-18)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Browser Foundation | 2 | 9 min | 4.5 min |
| 2. Cast Integration | 2 | 13 min | 6.5 min |
| 3. Video Pipeline | 3 | 11 min | 3.7 min |
| 4. Webhook API | 3 | 18 min | 6.0 min |
| 5. Production Readiness | 2 | 13 min | 6.5 min |
| 6. HTTP Streaming Server | 2 | 5 min | 2.5 min |
| 7. FFmpeg Dual-Mode | 2 | 8 min | 4.0 min |
| 8. Cast Media Playback | 1 | 15 min | 15.0 min |

## Accumulated Context

### Technical Debt (from v1.0)

Tracked for future milestones:

| Item | Severity | Source |
|------|----------|--------|
| Stream metadata tracking | Low | Phase 4 |
| Cast device name hardcoded | Low | Phase 4 |
| HTTP server for HLS streams | Medium | Phase 3 (✓ Resolved in Phase 6) |
| Hardware acceleration | Low | Phase 3 (design decision) |

### Pending Todos

3 todos pending. See `.planning/todos/pending/`

- **Direct RTSP to Cast streaming** — bypass browser capture for camera feeds (video)
- **Hardware acceleration (QuickSync/VAAPI)** — reduce CPU usage for FFmpeg encoding (v2)
- **FFmpeg process cleanup bug** — multiple FFmpeg processes spawned, not cleaned up on error (bug)
- **HLS stream buffering issue** — stream freezes after 6 seconds, needs HLS segment/timeout tuning (video)

### Blockers/Concerns

**Cast Playback Implementation** (Resolved):
- Cast device was receiving 404 errors when fetching HLS segments
- Root cause: STREAM_HOST_IP was 10.10.0.100 but Ubuntu machine is on 10.10.0.133
- **Resolution**: Updated docker-compose.yml STREAM_HOST_IP to 10.10.0.133
- **Status**: Resolved in Phase 8 - Cast playback working (video displays on TV)
- **Known issue**: Stream freezes after 6 seconds (HLS buffering issue, not Cast-related)

**FFmpeg Process Leak** (Active):
- Multiple FFmpeg processes (8+) spawned instead of 1 per stream
- Processes not cleaned up on error/restart
- Causes severe CPU load
- **Status**: Needs investigation - likely in FFmpegEncoder context manager cleanup

**WSL2 mDNS Limitation** (Resolved):
- mDNS discovery doesn't work in WSL2/Docker environment
- **Resolution**: CAST_DEVICE_IP environment variable for static IP configuration
- **Status**: Documented workaround available

## Session Continuity

Last session: 2026-01-18T10:36:28Z
Stopped at: Completed Phase 8 - v1.1 milestone shipped
Resume with: Ready for next milestone planning
Resume file: None

### Context for Next Session
- v1.1 Cast Media Playback milestone complete (3/3 phases)
- Cast playback working - video displays on TV
- Known issue: HLS stream freezes after 6 seconds (buffering tuning needed)
- System ready for production use with known buffering limitation
- Consider next milestones: RTSP streaming, hardware acceleration, or HLS buffering fixes
