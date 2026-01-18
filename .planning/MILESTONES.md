# Project Milestones: Dashboard Cast Service

## v1.1 Cast Media Playback (Shipped: 2026-01-18)

**Delivered:** Complete Cast playback pipeline with dual-mode streaming (HLS buffered + fMP4 low-latency).

**Phases completed:** 6-8 (5 plans total)

**Key accomplishments:**

- HTTP streaming server with CORS headers for Cast device LAN access
- Dual-mode FFmpeg encoding: HLS (buffered) and fMP4 (low-latency) streaming
- H.264 High Profile Level 4.1 + AAC audio for universal Cast compatibility
- Mode parameter flows through entire pipeline from webhook to Cast device
- Cast media playback verified working with video displaying on TV
- Network auto-detection with STREAM_HOST_IP configuration

**Stats:**

- 131 files created/modified (planning docs included)
- 2,094 lines of Python (total)
- 3 phases, 5 plans, 9 tasks
- 3 days from v1.1 start to ship (2026-01-15 → 2026-01-18)

**Git range:** `feat(06-01)` → `docs(08)`

**What's next:** Planning next milestone

**Known tech debt:** HLS stream freezes after 6 seconds (buffering configuration tuning needed)

---

## v1.0 Dashboard Cast Service (Shipped: 2026-01-16)

**Delivered:** Website-to-TV casting service triggered via a webhook.

**Phases completed:** 1-5 (12 plans total)

**Key accomplishments:**

- Playwright browser automation with auth injection (cookies + localStorage)
- Cast device discovery via mDNS with HDMI-CEC wake support
- FFmpeg video pipeline with quality presets (1080p, 720p, low-latency)
- FastAPI webhook API with async stream management
- Production-ready Docker deployment with comprehensive documentation
- WSL2 workaround with CAST_DEVICE_IP static IP configuration

**Stats:**

- 24 files created/modified
- 2,629 lines of Python
- 5 phases, 12 plans
- 2 days from project start to ship

**Git range:** `feat(01-01)` → `docs(05)`

**What's next:** TBD (discuss next milestone)

---
