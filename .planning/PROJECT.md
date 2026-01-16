# Dashboard Cast Service

## What This Is

A Docker service that receives webhook requests to render live webpages (dashboards, camera feeds) as video streams and casts them to Android TV devices. Uses Playwright for browser automation, FFmpeg for video encoding, and pychromecast for Cast protocol. Designed for smart home automation, particularly Home Assistant integrations.

## Core Value

Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.

## Requirements

### Validated

- ✓ HTTP webhook endpoint accepts URL and starts casting to configured Android TV — v1.0
- ✓ Render webpage to live video stream with configurable quality/fps — v1.0
- ✓ Cast video stream to Android TV device using Cast protocol — v1.0
- ✓ Handle authentication for local dashboards (cookies and localStorage injection) — v1.0
- ✓ Webhook endpoint to stop active cast — v1.0
- ✓ Single Android TV target (address configured in Docker or CAST_DEVICE_IP) — v1.0
- ✓ Video quality configurable via API (1080p, 720p, low-latency presets) — v1.0
- ✓ Support manual testing via curl — v1.0
- ✓ Continuous streaming until explicitly stopped or duration timeout — v1.0
- ✓ Docker container with minimal setup — v1.0
- ✓ Health check endpoint for monitoring — v1.0
- ✓ HDMI-CEC wake for TV — v1.0
- ✓ Retry with exponential backoff for Cast connections — v1.0
- ✓ Structured logging for debugging — v1.0
- ✓ WSL2 static IP workaround for mDNS limitation — v1.0
- ✓ Comprehensive documentation with Home Assistant examples — v1.0

### Active

(None — defining next milestone)

### Out of Scope

- Multiple simultaneous devices — single device target for v1, architecture allows future expansion
- Public/cloud-hosted dashboards — focused on local network Home Assistant use case
- Video recording/storage — streaming only, no persistence
- Complex authentication flows — supporting token/cookie-based auth only, not OAuth/2FA
- Desktop/mobile casting — Android TV only, different protocols
- GUI/web interface — API-only service for automation
- Offline mode — real-time streaming is core value

## Context

**Shipped v1.0** with 2,629 LOC Python.

**Tech stack:** Python 3.11, FastAPI, Playwright, pychromecast, FFmpeg, Xvfb, Docker

**Primary use case:** Home Assistant automations triggering dashboard displays on Android TV based on events (doorbell → camera feed, motion sensor → security dashboard).

**Architecture:**
- BrowserManager: Playwright chromium with auth injection
- CastSessionManager: pychromecast with HDMI-CEC wake
- StreamManager: Orchestrates Xvfb → Browser → FFmpeg → Cast
- FastAPI: Webhook endpoints (/start, /stop, /status, /health)

**Known limitations:**
- mDNS discovery doesn't work in WSL2 (CAST_DEVICE_IP workaround available)
- Single device only (architecture designed for future multi-device)
- Software encoding only (hardware acceleration deferred to v2)

## Constraints

- **Deployment**: Docker container — must be self-contained and easy to deploy
- **Network**: Local network operation — dashboards and Android TV on same LAN
- **Protocol**: Cast protocol for Android TV — must use compatible casting method
- **Performance**: Real-time video streaming — low latency between webpage updates and TV display
- **Authentication**: Flexible auth handling — support both env-configured and per-request credentials

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Webhook-based control (start/stop) | Enables Home Assistant automation integration | ✓ Good — Clean API, works with Home Assistant REST commands |
| Configurable quality via API | Balance between simplicity and flexibility | ✓ Good — Three presets (1080p, 720p, low-latency) cover most use cases |
| Single device with multi-device architecture | Ship faster with single device, avoid over-engineering | ✓ Good — Shipped fast, architecture ready for expansion |
| Support both auth methods (cookies + localStorage) | Some dashboards use tokens, others use sessions | ✓ Good — Covers Home Assistant and Frigate use cases |
| Playwright over Selenium | Better async support and Docker compatibility | ✓ Good — Cleaner code, reliable in containers |
| Context manager pattern everywhere | Automatic resource cleanup prevents leaks | ✓ Good — No memory leaks in long-running sessions |
| Fresh browser per request | Avoids memory leaks and stale auth | ✓ Good — Reliable across many cast sessions |
| Software encoding for v1 | Hardware acceleration varies by deployment target | ✓ Good — Works everywhere, NVENC/VAAPI/QSV for v2 |
| CAST_DEVICE_IP static IP fallback | WSL2 mDNS limitation workaround | ✓ Good — Unblocks WSL2/Docker users |
| asyncio.create_task for streams | Long-running streams outlive request lifecycle | ✓ Good — Clean async pattern |
| Auto-stop on new /start | Seamless transition for single-device use case | ✓ Good — No manual cleanup needed |

---
*Last updated: 2026-01-16 after v1.0 milestone*
