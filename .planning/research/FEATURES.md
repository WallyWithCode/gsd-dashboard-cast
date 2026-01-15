# Feature Research

**Domain:** Web-to-video streaming service with Cast protocol integration
**Researched:** 2026-01-15
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Webhook trigger endpoint | Standard for automation integrations | LOW | Simple HTTP POST endpoint with webhook_id routing |
| Device discovery (mDNS) | Cast protocol requirement | MEDIUM | pychromecast handles this, needs multicast UDP port 5353 |
| Basic playback control (start/stop) | Core Cast functionality | LOW | Required to initiate and terminate cast sessions |
| Volume control (0.0-1.0) | Standard Cast API feature | LOW | pychromecast MediaController provides this |
| Status reporting (active/idle) | Users need to know cast state | LOW | CastStatus includes is_active_input, is_stand_by, app_id, session_id |
| Authentication handling | Dashboards require login | HIGH | Chromecasts don't support login - must inject auth tokens/cookies into browser session |
| Browser rendering | Must render authenticated web content | MEDIUM | Docker + Puppeteer/Selenium for headless Chrome with authentication |
| HTTPS requirement | Cast security requirement | LOW | Chromecast only works with HTTPS websites |
| Session persistence | Prevent 10-minute idle timeout | MEDIUM | Known Cast limitation - requires periodic keepalive or custom receiver app |
| Error handling & logging | Debugging cast failures | LOW | Essential for webhook-triggered automation debugging |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Quality/resolution configuration | Optimize for network/device capabilities | MEDIUM | Home Assistant lacks this - frequently requested feature. Browser viewport size control + bitrate settings |
| Configurable cast duration | Auto-stop after time period | LOW | Useful for scheduled dashboard displays (e.g., morning briefing) |
| Multiple dashboard profiles | Different URLs/auth per webhook | LOW | Single service supports multiple use cases |
| Volume scheduling | Different volumes per time/webhook | LOW | Quiet at night, louder during day for notifications |
| Automatic retry with backoff | Handle transient failures gracefully | MEDIUM | Network issues common in home automation environments |
| Health check endpoint | Monitor service availability | LOW | Standard Docker service practice |
| HDMI-CEC TV wake | Auto-wake TV when casting | MEDIUM | Android TV supports "One Touch Play" - reliability varies by TV manufacturer |
| Queue/playlist support | Sequential dashboard rotation | MEDIUM | Cast multiple URLs in sequence with timing control |
| Webhook response with status | Immediate feedback on success/failure | LOW | Return cast session info in HTTP response |
| Custom Cast receiver app | Bypass 10-min timeout, custom UI | HIGH | Requires Google Cast Console registration ($5 fee), 5-15min propagation delay |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time synchronization across devices | "Mirror to all TVs" | Cast doesn't support true multi-room sync, adds complexity | Sequential casting to multiple devices with small delay |
| Bidirectional webhook communication | "Notify when cast ends" | Webhooks are unidirectional by design | Polling status endpoint or push via MQTT/WebSocket |
| Built-in dashboard creation | "Don't want to build HTML" | Scope creep - not core value | Focus on casting existing dashboards (Home Assistant, Grafana, etc.) |
| On-device video transcoding | "Support all formats" | CPU-intensive, not needed for web dashboards | Let browser handle rendering via standard web codecs |
| User authentication in service | "Login via web UI" | Adds security surface, conflicts with webhook pattern | Use authentication tokens passed via webhook payload |
| Full Cast protocol implementation | "Support all Cast features" | Massive scope - 90% unused for dashboard casting | Use pychromecast library, focus on dashboard-specific features |
| Persistent browser instances | "Faster casting" | Memory leaks, stale auth, resource accumulation | Fresh browser instance per cast, clean slate |

## Feature Dependencies

```
[Webhook Control]
    └──requires──> [Browser Rendering]
                       └──requires──> [Authentication Handling]
                           └──requires──> [HTTPS Support]

[Session Persistence] ──enhances──> [Quality Configuration]
[HDMI-CEC Wake] ──enhances──> [Webhook Control]

[Custom Cast Receiver] ──conflicts──> [Default Media Receiver]
    (Custom receiver bypasses 10-min timeout but requires registration & propagation delay)

[Volume Control]
    └──requires──> [Device Discovery]
    └──requires──> [Active Cast Session]

[Status Reporting]
    └──requires──> [pychromecast MediaStatusListener]
    └──requires──> [CastStatusListener]
```

### Dependency Notes

- **Browser Rendering requires Authentication Handling:** Must inject auth tokens/cookies before page load to access protected dashboards
- **Session Persistence enhances Quality Configuration:** Longer sessions benefit more from optimized quality settings
- **HDMI-CEC Wake enhances Webhook Control:** Single webhook can both wake TV and start casting for seamless user experience
- **Custom Cast Receiver conflicts with Default Media Receiver:** Must choose one approach - custom receiver adds deployment complexity but solves timeout issues
- **Volume Control requires Active Cast Session:** Can't control volume until cast connection established
- **Status Reporting requires pychromecast Listeners:** Both CastStatusListener and MediaStatusListener needed for complete state tracking

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [x] **Webhook trigger endpoint** — Core automation trigger mechanism
- [x] **Device discovery via mDNS** — Find Cast devices on network (pychromecast)
- [x] **Browser rendering with auth** — Render authenticated dashboards (Puppeteer/Selenium in Docker)
- [x] **Basic playback control** — Start/stop casting to specified device
- [x] **Volume control** — Set volume level when starting cast
- [x] **HTTPS support** — Meet Cast security requirements
- [x] **Error logging** — Debug webhook failures in Home Assistant automations
- [x] **Docker containerization** — Easy deployment, includes Chrome + dependencies

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] **Quality/resolution configuration** — User reports "dashboard looks blurry"
- [ ] **Configurable cast duration** — User wants "show for 30 seconds then stop"
- [ ] **HDMI-CEC TV wake** — User reports "have to manually turn on TV first"
- [ ] **Automatic retry logic** — User reports "sometimes fails, works on second try"
- [ ] **Status reporting endpoint** — User wants "check if still casting from other automation"
- [ ] **Multiple webhook profiles** — User wants "different dashboards for morning/evening"
- [ ] **Health check endpoint** — User reports "service crashed, automation silently failing"

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Custom Cast receiver app** — Requires $5 registration fee, 15-min propagation, device registration for testing
- [ ] **Queue/playlist support** — Adds state management complexity, unclear if needed
- [ ] **Multi-device casting** — Network complexity, unclear use case for dashboard casting
- [ ] **WebSocket status updates** — Overkill for webhook pattern, polling sufficient
- [ ] **GUI configuration** — Conflicts with "Docker service" model, YAML config sufficient

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Webhook endpoint | HIGH | LOW | P1 |
| Device discovery | HIGH | LOW (pychromecast) | P1 |
| Browser rendering + auth | HIGH | MEDIUM | P1 |
| Playback control | HIGH | LOW | P1 |
| Volume control | HIGH | LOW | P1 |
| Error logging | HIGH | LOW | P1 |
| Docker packaging | HIGH | LOW | P1 |
| Quality configuration | MEDIUM | MEDIUM | P2 |
| Cast duration control | MEDIUM | LOW | P2 |
| HDMI-CEC wake | MEDIUM | MEDIUM | P2 |
| Retry logic | MEDIUM | MEDIUM | P2 |
| Status endpoint | MEDIUM | LOW | P2 |
| Health check | LOW | LOW | P2 |
| Multiple profiles | MEDIUM | LOW | P2 |
| Custom receiver app | LOW | HIGH | P3 |
| Playlist support | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch (MVP)
- P2: Should have, add when possible (post-validation)
- P3: Nice to have, future consideration (v2+)

## Competitor Feature Analysis

| Feature | DashCast (Home Assistant) | CATT (Cast All The Things) | continuously_casting_dashboards | Our Approach |
|---------|---------------------------|----------------------------|--------------------------------|--------------|
| Webhook trigger | Via HA service call | Command-line only | Via HA service call | Direct HTTP webhook endpoint |
| Authentication | Requires HA Cast auth flow | No auth support | Requires HA Cast auth | Browser-level auth injection (cookies/tokens) |
| Session persistence | 10-min timeout issue | 10-min timeout issue | Periodic re-casting | Keepalive + optional custom receiver |
| Quality control | No configuration | No configuration | No configuration | Configurable resolution/viewport |
| HDMI-CEC | Supported via pychromecast | Supported via pychromecast | Supported via pychromecast | Supported via pychromecast |
| Volume control | Yes | Yes | Yes (configurable per device) | Yes (per webhook call) |
| Device discovery | mDNS via pychromecast | mDNS via pychromecast | mDNS via pychromecast | mDNS via pychromecast |
| Docker deployment | HA add-on | Python package install | HA integration | Standalone Docker service |
| Multi-dashboard | Manual service calls | Manual commands | Time-based rotation config | Webhook-driven (flexible automation) |
| Status reporting | HA entity state | CLI output | HA entity state | HTTP status endpoint + logging |

**Key Differentiators:**
1. **Standalone Docker service** - Not tied to Home Assistant, works with any automation platform
2. **Direct webhook endpoint** - No Home Assistant service call wrapper needed
3. **Browser-level authentication** - More flexible than Cast-specific auth flows
4. **Quality configuration** - Addresses #1 user complaint in HA community
5. **Flexible automation model** - Webhook-driven means any system can trigger (Node-RED, n8n, IFTTT, etc.)

## Cast Protocol Capabilities Reference

Based on Google Cast official documentation and pychromecast implementation:

### Core Protocol Features
- **Namespaces:** connection, heartbeat, receiver, deviceauth, media
- **Transport:** Protocol Buffers over TLS connection on port 8009
- **Discovery:** mDNS/DNS-SD (multicast UDP port 5353)
- **Authentication:** Device certificate validation

### Media Control (urn:x-cast:com.google.cast.media)
- Play/pause/stop/seek
- Queue management (load, insert, remove, reorder)
- Volume control (level 0.0-1.0, mute)
- Playback rate
- Media status reporting (idle, buffering, playing, paused)
- Supported formats: MP4, WebM, MP3, FLAC, HLS, DASH

### Receiver Control (urn:x-cast:com.google.cast.receiver)
- Launch/stop applications
- Application ID routing
- Volume control (device-level)
- Set active input
- Receiver status (app_id, display_name, is_active_input, is_stand_by, volume)

### HDMI-CEC Features
- One Touch Play (wake TV and switch input)
- System Audio Control
- Device Power Off (turn off TV)
- Active Source management
- **Reliability:** Varies by TV manufacturer, not guaranteed

### Limitations & Constraints
- **10-minute idle timeout:** Default Media Receiver stops after 10min without activity
- **HTTPS only:** Security requirement for Cast receivers
- **No authentication:** Cast devices can't handle login flows - must be handled externally
- **Network requirements:** Sender and receiver must be on same network (unless using Guest Mode)
- **Registration delay:** Custom receivers take 5-15min to propagate after registration

## Home Assistant Cast Ecosystem Insights

### User Pain Points (from community forums)
1. **Resolution/quality issues** - "WTH still not able to set resolution when casting dashboard to UHD Chromecast" (481+ votes)
2. **10-minute timeout** - Most common complaint, various workarounds attempted
3. **Authentication complexity** - Home Assistant Cast requires OAuth flow, confusing for users
4. **Reliability** - "dashboards being laggy and only casting for a few minutes"
5. **Sizing issues** - "Cast - Size of Cards too big on Full HD Screen"

### Common Workarounds
- **Periodic re-casting:** continuously_casting_dashboards re-casts every N seconds
- **Developer mode tweaks:** Some users fix timeout via ADB developer settings
- **Custom DashCast configuration:** Power settings, screensaver adjustments
- **Volume scheduling:** Different volumes per device/time window

### Integration Patterns
- **IFTTT webhooks:** Trigger HA automations from external events
- **n8n workflows:** Complex multi-step automation with webhook triggers
- **Node-RED:** Visual automation with webhook nodes

## Technical Implementation Notes

### pychromecast Library Capabilities
- **Discovery:** Browser-based (ListenerBrowser) or manual device specification
- **Controllers:** MediaController, DashCastController, YouTubeController, PlexController
- **Listeners:** CastStatusListener, MediaStatusListener for state updates
- **CEC Control:** Can ignore active input when determining idle state
- **Examples:** media playback, queue management, discovery, YouTube, Plex

### Browser Rendering Options
1. **Puppeteer** - Most popular, official Chrome DevTools Protocol API
2. **Selenium** - Cross-browser support, mature ecosystem
3. **Browserless** - Hosted/containerized service with dashboards
4. **Playwright** - Microsoft alternative to Puppeteer

**Docker considerations:**
- Use official `puppeteer/puppeteer` or `selenium/standalone-chrome` images
- Include required dependencies (fonts, codecs) for dashboard rendering
- Handle authentication via cookies/localStorage injection before navigation
- Configure viewport size for quality control

### Cast Receiver Options

**Option A: Default Media Receiver (Recommended for MVP)**
- App ID: CC1AD845 (built-in constant)
- No registration required
- 10-minute idle timeout
- Sufficient for basic dashboard casting

**Option B: Styled Media Receiver**
- Requires registration → get custom App ID
- Customizable CSS/theme
- Still has 10-minute timeout
- $5 registration fee + 5-15min propagation

**Option C: Custom Web Receiver**
- Full control over timeout behavior
- Can disable idle timeout via CastReceiverOptions
- Requires web hosting for receiver HTML/JS
- $5 registration fee + device registration for testing
- Overkill for MVP, consider for v2 if timeout is major issue

## Sources

### Official Documentation
- [Google Cast API Overview](https://developers.google.com/cast/docs/overview) - HIGH confidence
- [Google Cast API Reference](https://developers.google.com/cast/docs/reference/) - HIGH confidence
- [Google Cast Registration](https://developers.google.com/cast/docs/registration) - HIGH confidence
- [HDMI-CEC Control Service (Android)](https://source.android.com/docs/devices/tv/hdmi-cec) - HIGH confidence
- [Puppeteer Docker Guide](https://pptr.dev/guides/docker) - HIGH confidence

### Home Assistant Ecosystem
- [Home Assistant Cast Integration](https://www.home-assistant.io/integrations/cast/) - HIGH confidence
- [Home Assistant Webhook Triggers](https://www.home-assistant.io/docs/automation/trigger/) - HIGH confidence
- [DashCast Component](https://github.com/AlexxIT/DashCast) - MEDIUM confidence (third-party)
- [continuously_casting_dashboards](https://github.com/b0mbays/continuously_casting_dashboards) - MEDIUM confidence (community integration)

### Technical Implementation
- [pychromecast GitHub](https://github.com/home-assistant-libs/pychromecast) - HIGH confidence (official HA library)
- [CATT (Cast All The Things)](https://github.com/skorokithakis/catt) - MEDIUM confidence (community tool)
- [Browserless Chrome Docker](https://hub.docker.com/r/browserless/chrome) - MEDIUM confidence

### Community Insights
- [Google Nest Hub as Dashboard with DashCast](https://community.home-assistant.io/t/google-nest-hub-as-dashboard-with-dashcast-add-on/460217) - MEDIUM confidence
- [WTH resolution control request](https://community.home-assistant.io/t/wth-still-not-able-to-set-resolution-when-casting-dashboard-to-uhd-chromecast/481633) - LOW confidence (anecdotal)
- [Chromecast idle timeout discussions](https://www.googlenestcommunity.com/t5/Streaming/Chromcast-Shutting-Off-While-Inactive/m-p/419552) - LOW confidence (user reports)

### Protocol Details
- [Chromecast Protocol Documentation](https://github.com/geraldnilles/Chromecast-Server/blob/master/docs/GoogleCastProtocol.markdown) - MEDIUM confidence (reverse-engineered)
- [cast-web protocol implementation](https://github.com/cast-web/protocol) - MEDIUM confidence (community implementation)

---
*Feature research for: Docker service for casting authenticated web dashboards to Android TV via webhooks*
*Researched: 2026-01-15*
*Primary use case: Home Assistant automation with webhook control*
