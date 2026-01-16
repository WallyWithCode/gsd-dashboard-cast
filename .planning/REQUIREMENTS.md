# Requirements: Dashboard Cast Service

**Defined:** 2026-01-15
**Core Value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Webhook API

- [x] **WEBHOOK-01**: Service accepts POST webhook to start casting with URL parameter
- [x] **WEBHOOK-02**: Service accepts POST webhook to stop active casting session
- [x] **WEBHOOK-03**: Webhook endpoints return immediate status (success/failure with session info)
- [x] **WEBHOOK-04**: Service logs all webhook requests and Cast operations for debugging
- [x] **WEBHOOK-05**: Webhook can specify cast duration (auto-stop after N seconds/minutes)

### Cast Protocol

- [x] **CAST-01**: Service discovers Cast devices on local network via mDNS
- [x] **CAST-02**: Service initiates casting to discovered Cast device
- [x] **CAST-03**: Service stops active casting session on command
- [x] **CAST-04**: Service wakes TV via HDMI-CEC when starting cast
- [x] **CAST-05**: Service automatically retries failed Cast connections with exponential backoff

### Browser Rendering

- [x] **BROWSER-01**: Service renders web page in headless Chrome browser
- [x] **BROWSER-02**: Service injects authentication cookies/tokens before page load
- [ ] **BROWSER-03**: Service only renders HTTPS URLs (Cast security requirement)
- [x] **BROWSER-04**: Service allows configurable video quality (resolution + bitrate presets)

### Infrastructure

- [x] **INFRA-01**: Service packaged as Docker container with all dependencies
- [x] **INFRA-02**: Service exposes health check endpoint for monitoring

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Webhook API

- **WEBHOOK-V2-01**: Multiple dashboard profiles (different URLs/auth per webhook ID)

### Cast Protocol

- **CAST-V2-01**: Volume control via webhook parameter (0.0-1.0 range)
- **CAST-V2-02**: Status reporting endpoint (query active/idle Cast state)
- **CAST-V2-03**: Custom Cast receiver app (bypass 10-minute idle timeout)

### Browser Rendering

- **BROWSER-V2-01**: Session persistence (reuse browser sessions across casts)
- **BROWSER-V2-02**: Multiple authentication methods (pre-configured in Docker + per-request)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multiple simultaneous devices | Single device target for v1 - architecture designed to allow future expansion |
| Public/cloud-hosted dashboards | Focused on local network Home Assistant use case |
| Video recording/storage | Streaming only, no persistence - not core value |
| Complex authentication flows | Supporting token/cookie-based auth only, not OAuth/2FA |
| Desktop/mobile casting | Android TV only - different protocols |
| GUI/web interface | API-only service for automation, not manual control |
| Real-time multi-device sync | Cast doesn't support true sync, adds massive complexity |
| Built-in dashboard creation | Scope creep - cast existing dashboards only |
| Bidirectional webhook communication | Webhooks are unidirectional - use polling for status |
| Persistent browser instances | Memory leaks and stale auth - research shows this anti-pattern fails |

## Traceability

Which phases cover which requirements. Updated by create-roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| WEBHOOK-01 | Phase 4 | Complete |
| WEBHOOK-02 | Phase 4 | Complete |
| WEBHOOK-03 | Phase 4 | Complete |
| WEBHOOK-04 | Phase 4 | Complete |
| WEBHOOK-05 | Phase 3 | Complete |
| CAST-01 | Phase 2 | Complete |
| CAST-02 | Phase 2 | Complete |
| CAST-03 | Phase 2 | Complete |
| CAST-04 | Phase 2 | Complete |
| CAST-05 | Phase 2 | Complete |
| BROWSER-01 | Phase 1 | Complete |
| BROWSER-02 | Phase 1 | Complete |
| BROWSER-03 | Phase 5 | Pending |
| BROWSER-04 | Phase 3 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-15*
*Last updated: 2026-01-15 after roadmap creation*
