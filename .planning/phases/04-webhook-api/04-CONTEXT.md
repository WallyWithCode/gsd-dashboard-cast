# Phase 4: Webhook API - Context

**Gathered:** 2026-01-16
**Status:** Ready for planning

<vision>
## How This Should Work

A simple REST API with start/stop endpoints, clean and minimal like Stripe's API style. The API is config-driven with runtime overrides — device and quality come from Docker config by default, but allow per-request overrides for flexibility.

When a `/start` request comes in while something is already casting, it should auto-stop the previous stream and start the new one seamlessly. This makes Home Assistant automations much simpler since they can just fire webhooks without tracking state.

The webhooks should return immediately (non-blocking) while streams start in the background. No timeouts waiting for browser/FFmpeg to spin up.

</vision>

<essential>
## What Must Be Nailed

- **State management** - Always know what's casting. Clear visibility into active streams, proper cleanup, never leave zombie processes running.
- **Non-blocking responses** - Webhooks return immediately, stream setup happens in background
- **Seamless transitions** - Auto-stop previous stream when new start request arrives

</essential>

<specifics>
## Specific Ideas

**API Shape:**
- POST `/start` with `{"url": "...", "quality": "1080p", "duration": 300}` (quality and duration optional, use Docker config defaults)
- POST `/stop` to stop active stream
- Returns `{"status": "success", "session_id": "..."}` or `{"success": true}` style responses

**Status endpoint:**
- GET `/status` returns current stream info (URL, quality, started_at, etc) or null if idle
- Easy to query from Home Assistant to check what's currently casting

**Structured logging:**
- Every webhook logged with timestamp, URL, device, outcome
- Makes troubleshooting Home Assistant automations easy

**Health check:**
- GET `/health` endpoint for Docker health checks and uptime monitoring
- Returns service status and dependencies

</specifics>

<notes>
## Additional Context

This phase completes the core functionality — after this, Phase 5 just packages everything for production deployment. The API is the interface between Home Assistant automations and the casting pipeline.

Key integration: Use StreamManager from Phase 3 for the actual streaming work. The API layer just handles HTTP, state tracking, and background job management.

</notes>

---

*Phase: 04-webhook-api*
*Context gathered: 2026-01-16*
