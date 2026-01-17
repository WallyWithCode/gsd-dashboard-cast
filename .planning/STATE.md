# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-16)

**Core value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.
**Current focus:** v1.1 Cast Media Playback — dual-mode streaming

## Current Position

Phase: 7.1 of 8 (Cast Playback Debug) — INSERTED
Plan: Not started
Status: Ready to plan
Last activity: 2026-01-17 — Debugging Cast black screen issue

Progress: ██████░░░░ 50% (v1.1 — 2/4 phases, inserted debug phase)

## Milestones

| Version | Name | Status | Shipped |
|---------|------|--------|---------|
| v1.1 | Cast Media Playback | 🚧 Active | — |
| v1.0 | Dashboard Cast Service | ✅ Shipped | 2026-01-16 |

See: .planning/MILESTONES.md for full milestone history.

## Performance Metrics

**v1.0 Velocity:**
- Total plans completed: 12
- Average duration: 5.3 min
- Total execution time: 1.07 hours
- Timeline: 2 days (2026-01-15 → 2026-01-16)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Browser Foundation | 2 | 9 min | 4.5 min |
| 2. Cast Integration | 2 | 13 min | 6.5 min |
| 3. Video Pipeline | 3 | 11 min | 3.7 min |
| 4. Webhook API | 3 | 18 min | 6.0 min |
| 5. Production Readiness | 2 | 13 min | 6.5 min |

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

4 todos pending. See `.planning/todos/pending/`

- **Implement Cast media playback** — HTTP server + media_controller.play_media() (video)
- **Direct RTSP to Cast streaming** — bypass browser capture for camera feeds (video)
- **Hardware acceleration (QuickSync/VAAPI)** — reduce CPU usage for FFmpeg encoding (v2)
- **FFmpeg process cleanup bug** — multiple FFmpeg processes spawned, not cleaned up on error (bug)

### Blockers/Concerns

**Cast Shows Black Screen / Loading Loop** (Active - MVP Blocker):
- Cast device receives connection (shows Cast icon, then loading bar)
- Then falls back to Cast logo - playback fails
- Debugging done:
  - ✓ HLS files created correctly (.m3u8 + .ts segments)
  - ✓ Playlist format is valid
  - ✓ HTTP server running on port 8080
  - ✓ Increased HLS buffer to 10 segments (20s)
  - ✗ Segments still returning 404 when Cast fetches
- Remaining investigation needed:
  - Verify Cast device can reach host IP (firewall?)
  - Test stream in VLC from another device on network
  - Check if encoding parameters are Cast-compatible
  - Try absolute URLs in playlist instead of relative
  - Check segment timing vs Cast fetch timing
- **Status**: Needs dedicated debug phase

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

Last session: 2026-01-17
Stopped at: Phase 7.1 inserted - Cast playback not working (black screen/loading loop)
Resume with: `/gsd:plan-phase 7.1` or `/gsd:debug` for systematic debugging
Resume file: None

### Debug Context for Next Session
- Cast device connects successfully (shows Cast icon)
- Loading bar appears briefly, then falls back to Cast logo
- HLS files are being created correctly (.m3u8 + .ts segments)
- Segments returning 404 when Cast tries to fetch them
- Already tried: increased hls_list_size to 10, added append_list flag
- Next steps: verify network accessibility, test stream in VLC, check segment timing
