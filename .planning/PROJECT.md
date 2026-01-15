# Dashboard Cast Service

## What This Is

A Docker service that receives webhook requests to render live webpages (dashboards, camera feeds) as video streams and casts them to Android TV devices. Designed for smart home automation, particularly Home Assistant integrations, with webhook-based start/stop control.

## Core Value

Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] HTTP webhook endpoint accepts URL and starts casting to configured Android TV
- [ ] Render webpage to live video stream with configurable quality/fps
- [ ] Cast video stream to Android TV device using Cast protocol
- [ ] Handle authentication for local dashboards (both pre-configured and per-request credentials)
- [ ] Webhook endpoint to stop active cast
- [ ] Single Android TV target (address configured in Docker)
- [ ] Video quality configurable via Docker config and API
- [ ] Support manual testing via curl/Postman
- [ ] Continuous streaming until explicitly stopped
- [ ] Docker container with minimal setup

### Out of Scope

- Multiple simultaneous devices — single device target for v1, architecture should allow future expansion
- Public/cloud-hosted dashboards — focused on local network Home Assistant use case
- Video recording/storage — streaming only, no persistence
- Complex authentication flows — supporting token/cookie-based auth only
- Desktop/mobile casting — Android TV only
- GUI/web interface — API-only service

## Context

**Primary use case:** Home Assistant automations triggering dashboard displays on Android TV based on events (doorbell → camera feed, motion sensor → security dashboard, etc.)

**Target environment:**
- Local home network
- Docker deployment on home server/NAS
- Dashboards with authentication (Home Assistant, Frigate, etc.)
- Single Android TV initially, but design should accommodate multi-device expansion

**Key challenge:** Rendering live web content to video stream while maintaining authentication session, then reliably casting to Android TV via simple webhook API.

## Constraints

- **Deployment**: Docker container — must be self-contained and easy to deploy
- **Network**: Local network operation — dashboards and Android TV on same LAN
- **Protocol**: Cast protocol for Android TV — must use compatible casting method
- **Performance**: Real-time video streaming — low latency between webpage updates and TV display
- **Authentication**: Flexible auth handling — support both env-configured and per-request credentials

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Webhook-based control (start/stop) | Enables Home Assistant automation integration | — Pending |
| Configurable quality via Docker + API | Balance between simplicity (Docker config) and flexibility (runtime API) | — Pending |
| Single device with multi-device architecture | Ship faster with single device, avoid over-engineering, but don't paint into corner | — Pending |
| Support both auth methods | Some dashboards use long-lived tokens (config), others need session-based (per-request) | — Pending |

---
*Last updated: 2026-01-15 after initialization*
