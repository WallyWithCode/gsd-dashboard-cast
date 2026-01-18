# Roadmap: Dashboard Cast Service v2.0

## Overview

v2.0 Stability and Hardware Acceleration transforms the system from proof-of-concept to production-ready service. Five phases address critical operational issues: fix HLS buffering freeze (6-second bug), validate low-latency fMP4 mode, detect device-initiated stops, implement robust process lifecycle management, and integrate Intel QuickSync hardware acceleration with graceful fallback. Each phase independently deployable and provides value even if later phases deferred.

## Milestones

- ✅ **v1.0 MVP** - Phases 1-4 (shipped 2026-01-15)
- ✅ **v1.1 Cast Media Playback** - Phases 5-8 (shipped 2026-01-18)
- 🚧 **v2.0 Stability and Hardware Acceleration** - Phases 9-13 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) - SHIPPED 2026-01-15</summary>

See: .planning/milestones/v1.0-ROADMAP.md

</details>

<details>
<summary>✅ v1.1 Cast Media Playback (Phases 5-8) - SHIPPED 2026-01-18</summary>

See: .planning/milestones/v1.1-ROADMAP.md

</details>

### 🚧 v2.0 Stability and Hardware Acceleration (In Progress)

**Milestone Goal:** Production-ready reliability with hardware-accelerated encoding and robust stream lifecycle management.

#### Phase 9: HLS Buffering Fix
**Goal:** HLS streams play indefinitely without freezing
**Depends on:** Nothing (independent configuration change)
**Requirements:** HLS-01, HLS-02, HLS-03, HLS-04, HLS-05
**Success Criteria** (what must be TRUE):
  1. HLS stream plays for 5+ minutes without freezing on Cast device
  2. Cast device maintains 40-60 second buffer window during playback
  3. Stream continues indefinitely until explicitly stopped via webhook
  4. No stale HLS segments remain in /tmp/streams/ after session ends
**Research:** Unlikely (established patterns)
**Plans:** 2 plans

Plans:
- [ ] 09-01-PLAN.md — HLS buffering configuration fix and startup cleanup
- [ ] 09-02-PLAN.md — FFmpeg subprocess log forwarding (gap closure)

#### Phase 10: fMP4 Low-Latency Validation
**Goal:** fMP4 low-latency mode validated and working correctly
**Depends on:** Nothing (independent validation of existing feature)
**Requirements:** FMP4-01, FMP4-02, FMP4-03, FMP4-04
**Success Criteria** (what must be TRUE):
  1. fMP4 stream plays without freezing on Cast device
  2. Low-latency mode achieves <2 second glass-to-glass latency
  3. Range requests work correctly between Cast device and aiohttp server
  4. MIME type and CORS headers return correct values for fMP4 streams
**Research:** Unlikely (validation testing)
**Plans:** TBD

Plans:
- [ ] 10-01: TBD (during planning)

#### Phase 11: Cast Session State Monitoring
**Goal:** Device-initiated stop detection enables automatic cleanup
**Depends on:** Nothing (foundation for process management)
**Requirements:** PROC-01, PROC-02
**Success Criteria** (what must be TRUE):
  1. Service detects when user stops cast from TV remote
  2. Application receives notification within 2 seconds of device stop
  3. Stopping from TV remote triggers cleanup callback
**Research:** Unlikely (standard pychromecast usage)
**Plans:** TBD

Plans:
- [ ] 11-01: TBD (during planning)

#### Phase 12: Process Lifecycle Management
**Goal:** FFmpeg processes automatically cleaned up with zero orphans
**Depends on:** Phase 11 (session monitoring provides stop detection)
**Requirements:** PROC-03, PROC-04, PROC-05, PROC-06, PROC-07, OPER-02, OPER-03
**Success Criteria** (what must be TRUE):
  1. FFmpeg terminates within 5 seconds when cast stops from device
  2. No orphaned FFmpeg processes after stop/start cycles
  3. Docker SIGTERM triggers graceful shutdown of all active streams
  4. Service remains stable after 10+ consecutive start/stop cycles
**Research:** Unlikely (standard Python asyncio patterns)
**Plans:** TBD

Plans:
- [ ] 12-01: TBD (during planning)

#### Phase 13: Intel QuickSync Hardware Acceleration
**Goal:** Hardware acceleration reduces CPU usage by 80-90% per stream
**Depends on:** Phase 12 (stable process management required before hardware complexity)
**Requirements:** HWAC-01, HWAC-02, HWAC-03, HWAC-04, HWAC-05, HWAC-06, HWAC-07, OPER-01, OPER-04
**Success Criteria** (what must be TRUE):
  1. h264_qsv encoder encodes 1080p stream at <20% CPU on Intel CPU
  2. Service gracefully falls back to software encoding if QuickSync unavailable
  3. Health check endpoint reports hardware acceleration status
  4. Proxmox GPU passthrough documentation enables /dev/dri access
  5. Docker container correctly accesses /dev/dri/renderD128 with render group
**Research:** Likely (Proxmox GPU passthrough)
**Research topics:** IOMMU group conflicts, driver selection (iHD vs i965) per CPU generation
**Plans:** TBD

Plans:
- [ ] 13-01: TBD (during planning)

## Progress

**Execution Order:**
Phases execute in numeric order: 9 → 10 → 11 → 12 → 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Project Foundation | v1.0 | 3/3 | Complete | 2026-01-14 |
| 2. Video Encoding Pipeline | v1.0 | 2/2 | Complete | 2026-01-15 |
| 3. Cast Protocol Integration | v1.0 | 3/3 | Complete | 2026-01-15 |
| 4. Continuous Streaming | v1.0 | 2/2 | Complete | 2026-01-15 |
| 5. HTTP Streaming Foundation | v1.1 | 2/2 | Complete | 2026-01-17 |
| 6. HLS Buffered Streaming | v1.1 | 3/3 | Complete | 2026-01-17 |
| 7. fMP4 Low-Latency Streaming | v1.1 | 3/3 | Complete | 2026-01-18 |
| 8. Cast Media Playback | v1.1 | 2/2 | Complete | 2026-01-18 |
| 9. HLS Buffering Fix | v2.0 | 0/2 | Not started | - |
| 10. fMP4 Low-Latency Validation | v2.0 | 0/? | Not started | - |
| 11. Cast Session State Monitoring | v2.0 | 0/? | Not started | - |
| 12. Process Lifecycle Management | v2.0 | 0/? | Not started | - |
| 13. Intel QuickSync Hardware Acceleration | v2.0 | 0/? | Not started | - |

---
*Roadmap created: 2026-01-18 for v2.0 Stability and Hardware Acceleration*
