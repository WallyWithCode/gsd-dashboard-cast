# Architecture Research

**Domain:** Web-to-video streaming service with Cast protocol integration
**Researched:** 2026-01-15
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Webhook API  │  │ Control API  │  │ Status API   │               │
│  │ (Trigger)    │  │ (Start/Stop) │  │ (Health)     │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                  │                       │
├─────────┴─────────────────┴──────────────────┴───────────────────────┤
│                    Orchestration Layer                               │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │              Session Manager                                │     │
│  │  - Authentication persistence                               │     │
│  │  - Stream lifecycle management                              │     │
│  │  - Quality configuration                                    │     │
│  └────────┬───────────────────────┬───────────────────────────┘     │
│           │                       │                                  │
├───────────┴───────────────────────┴──────────────────────────────────┤
│                    Processing Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  Browser     │  │  Video       │  │  Cast        │               │
│  │  Engine      │→ │  Encoder     │→ │  Client      │               │
│  │ (Chromium)   │  │  (FFmpeg)    │  │ (CASTV2)     │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│         ↑                  ↑                                         │
│         │                  │                                         │
│  ┌──────────────┐  ┌──────────────┐                                 │
│  │   Xvfb       │  │  PipeWire/   │                                 │
│  │  (Virtual    │  │  PulseAudio  │                                 │
│  │   Display)   │  │  (Audio)     │                                 │
│  └──────────────┘  └──────────────┘                                 │
├─────────────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Docker     │  │   Network    │  │   Storage    │               │
│  │  Container   │  │   Bridge     │  │  (Sessions)  │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Webhook API | Receives trigger events to start streaming | Express/Fastify REST endpoint with validation |
| Control API | Manages stream lifecycle (start/stop/configure) | RESTful endpoints with session management |
| Status API | Health checks and stream status monitoring | GET endpoints returning stream state and metrics |
| Session Manager | Maintains browser authentication and stream state | In-memory state with persistent cookie storage |
| Browser Engine | Renders target web page/dashboard | Puppeteer controlling headless Chromium |
| Video Encoder | Captures frames and encodes to H.264 | FFmpeg with CDP screencast frames or Xvfb capture |
| Cast Client | Streams video to Chromecast device | node-castv2-client library over TLS port 8009 |
| Xvfb | Provides virtual display for browser | X Virtual Framebuffer (Xvfb) creating display buffer |
| Audio System | Virtual audio device for sound capture | PipeWire (preferred) or PulseAudio |

## Recommended Project Structure

```
src/
├── api/                # API layer
│   ├── routes/         # Route handlers
│   │   ├── webhook.ts  # Webhook trigger endpoint
│   │   ├── control.ts  # Start/stop/configure endpoints
│   │   └── status.ts   # Health and status endpoints
│   ├── middleware/     # Request validation, auth
│   └── server.ts       # Express/Fastify app setup
├── session/            # Session management
│   ├── manager.ts      # Session lifecycle and state
│   ├── auth.ts         # Authentication persistence
│   └── storage.ts      # Cookie/session storage
├── browser/            # Browser automation
│   ├── launcher.ts     # Puppeteer browser lifecycle
│   ├── navigator.ts    # Page navigation and control
│   └── capture.ts      # CDP screencast capture
├── encoder/            # Video encoding
│   ├── ffmpeg.ts       # FFmpeg pipeline management
│   ├── quality.ts      # Bitrate/resolution config
│   └── stream.ts       # Stream output handling
├── cast/               # Cast integration
│   ├── client.ts       # CASTV2 client connection
│   ├── discovery.ts    # Device discovery (mDNS)
│   └── protocol.ts     # Cast protocol handlers
├── config/             # Configuration
│   ├── defaults.ts     # Default settings
│   └── validation.ts   # Config schema validation
└── types/              # TypeScript types
    ├── api.ts          # API request/response types
    ├── session.ts      # Session state types
    └── cast.ts         # Cast protocol types
```

### Structure Rationale

- **api/:** Separates HTTP concerns from business logic, enabling easy testing and route modifications
- **session/:** Centralizes authentication and state management, critical for maintaining long-lived browser sessions
- **browser/:** Encapsulates Puppeteer complexity, making it easy to swap automation libraries if needed
- **encoder/:** Isolates FFmpeg pipeline, allowing quality tuning without affecting other components
- **cast/:** Contains all Cast protocol specifics, enabling support for additional protocols later
- **config/:** Single source of truth for configuration with validation

## Architectural Patterns

### Pattern 1: Pipeline Architecture

**What:** Sequential processing stages where each component transforms data and passes it to the next stage. Webhook → Browser → Encoder → Cast forms a data pipeline.

**When to use:** Ideal for video streaming where data flows unidirectionally through transformation stages with clear boundaries.

**Trade-offs:**
- Pros: Clear separation of concerns, easy to debug individual stages, supports backpressure handling
- Cons: Pipeline breaks if any stage fails, end-to-end latency is sum of all stages, harder to parallelize

**Example:**
```typescript
// Pipeline orchestrator
class StreamPipeline {
  constructor(
    private browser: BrowserCapture,
    private encoder: VideoEncoder,
    private cast: CastClient
  ) {}

  async start(url: string, config: QualityConfig) {
    // Stage 1: Browser renders page
    const frameStream = await this.browser.startCapture(url);

    // Stage 2: Encoder processes frames
    const videoStream = await this.encoder.encode(frameStream, config);

    // Stage 3: Cast client streams to device
    await this.cast.stream(videoStream);
  }
}
```

### Pattern 2: Session-Based State Management

**What:** Maintain long-lived browser sessions with persistent authentication across multiple streaming requests. Store cookies and session data between invocations.

**When to use:** Required when the target website requires authentication or when avoiding repeated logins improves performance (reduces startup time by ~70%).

**Trade-offs:**
- Pros: Eliminates re-authentication overhead, maintains user context, faster stream startup
- Cons: Requires session storage, cookies can expire, multiple concurrent sessions need isolation, security considerations for stored credentials

**Example:**
```typescript
// Session persistence
class SessionManager {
  private sessions = new Map<string, BrowserSession>();

  async getOrCreate(sessionId: string, authConfig: AuthConfig): Promise<BrowserSession> {
    let session = this.sessions.get(sessionId);

    if (!session || await this.isExpired(session)) {
      // Create new session with persistent user data directory
      session = await this.createSession(sessionId, {
        userDataDir: `/data/sessions/${sessionId}`,
        cookies: await this.loadCookies(sessionId)
      });

      if (authConfig) {
        await this.authenticate(session, authConfig);
      }

      this.sessions.set(sessionId, session);
    }

    return session;
  }

  async isExpired(session: BrowserSession): Promise<boolean> {
    // Validate session before workflow execution (reduces failures by 78%)
    try {
      return !(await session.page.evaluate(() => {
        // Check authentication state
        return !!document.querySelector('[data-authenticated]');
      }));
    } catch {
      return true;
    }
  }
}
```

### Pattern 3: Quality-Adaptive Configuration

**What:** Allow runtime configuration of video quality parameters (resolution, bitrate, framerate) to balance quality, bandwidth, and CPU usage.

**When to use:** When supporting multiple network conditions or Cast device capabilities, or when optimizing for specific use cases (low latency vs high quality).

**Trade-offs:**
- Pros: Flexible quality control, can optimize for bandwidth or CPU constraints, supports multiple device types
- Cons: More complex configuration, requires understanding of encoding parameters, wrong settings can cause poor quality or high latency

**Example:**
```typescript
// Quality configuration presets
interface QualityConfig {
  resolution: { width: number; height: number };
  bitrate: number; // kbps
  framerate: number;
  preset: 'ultrafast' | 'fast' | 'medium' | 'slow';
  latency: 'low' | 'normal';
}

const QUALITY_PRESETS: Record<string, QualityConfig> = {
  '1080p': {
    resolution: { width: 1920, height: 1080 },
    bitrate: 5000,
    framerate: 30,
    preset: 'medium',
    latency: 'normal'
  },
  '720p': {
    resolution: { width: 1280, height: 720 },
    bitrate: 2500,
    framerate: 30,
    preset: 'fast',
    latency: 'normal'
  },
  'low-latency': {
    resolution: { width: 1280, height: 720 },
    bitrate: 2000,
    framerate: 30,
    preset: 'ultrafast', // Sacrifices compression for speed
    latency: 'low'
  }
};

class VideoEncoder {
  buildFFmpegArgs(config: QualityConfig): string[] {
    const args = [
      '-f', 'x11grab',
      '-video_size', `${config.resolution.width}x${config.resolution.height}`,
      '-framerate', String(config.framerate),
      '-i', ':99', // Xvfb display
      '-c:v', 'libx264',
      '-preset', config.preset,
      '-b:v', `${config.bitrate}k`,
    ];

    if (config.latency === 'low') {
      // Low latency encoding: IP frames only, no reordering
      args.push(
        '-tune', 'zerolatency',
        '-g', String(config.framerate), // Keyframe every second
        '-bf', '0', // No B-frames
        '-refs', '1', // Single reference frame
        '-max_delay', '0'
      );
    } else {
      // Normal latency: better compression
      args.push(
        '-g', String(config.framerate * 2), // Keyframe every 2 seconds
        '-bf', '2', // Use B-frames
        '-refs', '3'
      );
    }

    return args;
  }
}
```

## Data Flow

### Request Flow

```
[Webhook Event]
    ↓
[API Handler] → [Validation] → [Session Manager] → [Pipeline Orchestrator]
    ↓              ↓                  ↓                      ↓
[Response]    [Auth Check]    [Get/Create Session]   [Start Pipeline]
                                     ↓
                              [Browser Launch]
                                     ↓
                              [Navigate to URL]
                                     ↓
                         [Start CDP Screencast/Xvfb]
                                     ↓
                              [FFmpeg Capture]
                                     ↓
                              [Encode H.264]
                                     ↓
                              [Cast Connection]
                                     ↓
                           [Stream to Chromecast]
```

### Cast Protocol Flow

```
[Cast Client]
    ↓
[mDNS Discovery] → Find Chromecast devices on local network
    ↓
[TLS Connection] → Connect to device on port 8009
    ↓
[Virtual Connection] → Establish via urn:x-cast:com.google.cast.tp.connection
    ↓
[Launch App] → Send LAUNCH command to receiver-0
    ↓
[Load Media] → Send LOAD with media URL to application
    ↓
[Heartbeat Loop] → Send PING every 5 seconds to maintain connection
    ↓
[Media Streaming] → Device fetches video stream via URL
    ↓
[Status Updates] → Receive playback status broadcasts
    ↓
[Stop/Disconnect] → Send STOP and close virtual connection
```

### Video Capture Methods

The architecture supports two primary video capture approaches:

#### Method 1: Chrome DevTools Protocol (CDP) Screencast
```
[Puppeteer Page]
    ↓
[Page.startScreencast()] → CDP captures individual frames as PNG/JPEG
    ↓
[screencastFrame events] → Receive base64-encoded frame data
    ↓
[Frame Buffer] → Accumulate frames in memory
    ↓
[FFmpeg stdin] → Pipe frames to FFmpeg for encoding
    ↓
[H.264 Stream] → Output encoded video
```

#### Method 2: Xvfb Virtual Display Capture
```
[Xvfb :99] → Virtual X11 framebuffer (e.g., 1920x1080)
    ↓
[Chromium --display=:99] → Browser renders to virtual display
    ↓
[FFmpeg x11grab] → Capture display buffer directly
    ↓
[H.264 Encoding] → Real-time encoding
    ↓
[Video Stream Output] → RTMP/HLS/Direct streaming
```

**Method Comparison:**
- **CDP Screencast:** Lower CPU, works in true headless mode, but limited to ~20 FPS, adds frame-stitching complexity
- **Xvfb Capture:** Higher FPS (30-60), simpler FFmpeg pipeline, but requires X11 in container, higher memory usage

### Key Data Flows

1. **Webhook Trigger Flow:** External system sends webhook → API validates payload → Session manager checks for existing session → Either resume existing stream or create new pipeline → Return stream ID and status

2. **Authentication Persistence Flow:** Load cookies from persistent storage → Launch browser with user data directory → Validate authentication state → If expired, re-authenticate → Store updated cookies → Proceed with streaming

3. **Quality Adaptation Flow:** Client specifies quality preset or custom config → Encoder configures FFmpeg parameters (bitrate, resolution, preset) → Monitor encoding performance → If CPU overload detected, can dynamically reduce quality

4. **Error Recovery Flow:** Pipeline stage fails → Stop downstream stages → Clean up resources (close browser, kill FFmpeg) → Log error and notify client → Maintain session data for retry → If retry requested, resume from last good state

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-5 concurrent streams | Single Docker container with shared Xvfb instances, in-memory session storage, direct Cast connections. Minimal orchestration needed. |
| 5-20 concurrent streams | Multiple Docker containers behind load balancer, persistent session storage (Redis), separate containers for browser + encoder, dedicated Xvfb per stream. Monitor CPU/memory limits. |
| 20+ concurrent streams | Kubernetes orchestration, separate node pools for browser/encoding workloads, distributed session storage, potential hardware encoding (NVENC/QSV), stream queueing system, horizontal pod autoscaling. |

### Scaling Priorities

1. **First bottleneck: CPU encoding**
   - What breaks: FFmpeg H.264 encoding is CPU-intensive; 2-3 1080p streams will max out a 4-core CPU
   - How to fix: Use hardware encoding (NVENC on NVIDIA, QSV on Intel), reduce quality preset (medium→fast→ultrafast), lower resolution/framerate, or scale to multiple encoding containers

2. **Second bottleneck: Browser memory**
   - What breaks: Each Chromium instance uses 200-500MB RAM; long-running sessions leak memory; 10+ browser instances exhaust 8GB RAM
   - How to fix: Implement browser instance pooling with TTL, restart browsers periodically (every 1-2 hours), use --disable-dev-shm-usage flag, increase container memory limits, or use lighter browsers (playwright-webkit)

3. **Third bottleneck: Network bandwidth**
   - What breaks: Multiple 5Mbps streams saturate 100Mbps network connection; Cast devices compete for bandwidth
   - How to fix: Deploy geographically distributed instances, use adaptive bitrate, implement quality tier caps, monitor per-stream bandwidth

## Anti-Patterns

### Anti-Pattern 1: Restarting Browser Per Stream

**What people do:** Launch a new Chromium instance for every streaming request, including re-authentication each time

**Why it's wrong:**
- Browser startup takes 3-5 seconds
- Re-authentication adds 5-10 seconds
- Increases CPU/memory churn
- Wastes 70% of time on setup vs actual streaming

**Do this instead:** Maintain persistent browser sessions with authentication, use Puppeteer's user data directory for cookie persistence, implement session validation to detect expiration, reuse browser instances across requests

### Anti-Pattern 2: Using Default FFmpeg Settings

**What people do:** Run FFmpeg with minimal flags like `ffmpeg -i input output.mp4` assuming defaults are good

**Why it's wrong:**
- Default CRF of 23 optimizes for quality over latency
- No tuning for real-time encoding causes frame drops
- B-frames increase latency (reordering delay)
- Adaptive bitrate not configured causes bandwidth spikes

**Do this instead:** Explicitly configure encoder settings for streaming use case:
```bash
ffmpeg -f x11grab -i :99 \
  -c:v libx264 -preset ultrafast \  # Fast encoding
  -tune zerolatency \                # No frame reordering
  -bf 0 \                            # No B-frames
  -g 30 \                            # Keyframe every second
  -b:v 2500k -maxrate 2500k \       # Constant bitrate
  -bufsize 5000k \                   # Buffer for rate control
  -f mpegts output.ts                # Streamable format
```

### Anti-Pattern 3: Ignoring Xvfb Display Management

**What people do:** Start Xvfb once at container startup and share it across all browser instances

**Why it's wrong:**
- Multiple browsers drawing to same display creates visual artifacts
- Cannot capture individual streams separately
- Resolution mismatches between streams cause rendering issues
- Browser crashes affect all streams on that display

**Do this instead:**
- Create dedicated Xvfb display per stream (`:99`, `:100`, etc.)
- Set display resolution to match target stream quality
- Clean up Xvfb process when stream ends
- Use Xvfb's `-screen 0 1920x1080x24` to specify display properties
- Monitor and restart hung Xvfb processes

### Anti-Pattern 4: Blocking API Responses on Stream Start

**What people do:** Webhook handler waits for entire pipeline to initialize before returning response

**Why it's wrong:**
- Browser launch + navigation takes 5-15 seconds
- FFmpeg startup and Cast connection add more delay
- Webhook caller times out (typically 30 seconds)
- Prevents handling multiple simultaneous requests

**Do this instead:**
- Return 202 Accepted immediately with stream ID
- Start pipeline asynchronously in background
- Provide separate status endpoint to poll progress
- Use webhooks or WebSockets to notify when stream is live
- Implement proper error handling and reporting

### Anti-Pattern 5: Hardcoding Cast Device Selection

**What people do:** Configure a single static Cast device IP or name in configuration

**Why it's wrong:**
- Devices can change IP addresses (DHCP)
- Cannot support multiple Cast devices
- Device may be offline or unavailable
- No fallback mechanism

**Do this instead:**
- Implement mDNS discovery to find available Cast devices dynamically
- Allow device selection via API parameter (by name or ID)
- Cache discovered devices with TTL
- Provide device list endpoint for client selection
- Implement connection retry with fallback devices

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Webhook Source | HTTP POST to trigger endpoint | Validate signature, implement idempotency, support retry with exponential backoff |
| Target Website | Browser automation (Puppeteer) | Handle authentication, manage session cookies, detect and handle CAPTCHAs, respect robots.txt |
| Chromecast Device | CASTV2 protocol over TLS | mDNS discovery, maintain heartbeat (5s interval), handle device disconnection gracefully |
| Session Storage | File system or Redis | Store cookies and session state, implement TTL for cleanup, consider encryption for sensitive data |
| Monitoring/Logging | Structured logging + metrics | Log pipeline events, track encoding metrics, alert on failures, dashboards for stream health |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API ↔ Session Manager | Direct function calls | Synchronous for session lookup, async for session creation |
| Session Manager ↔ Browser | Puppeteer API | Async operations, handle timeouts (30s navigation, 60s authentication) |
| Browser ↔ Encoder | Pipe/Stream or CDP events | Backpressure handling crucial, monitor buffer sizes to prevent memory bloat |
| Encoder ↔ Cast Client | HTTP/RTMP URL or direct pipe | Cast client fetches stream via URL (indirect) or receives piped data (direct) |
| Components ↔ Config | Import from config module | Centralized configuration with validation, support environment overrides |

## Sources

### Google Cast Protocol (HIGH Confidence)
- [Overview | Cast | Google for Developers](https://developers.google.com/cast/docs/overview) - Official Cast documentation
- [Web Receiver Player Streaming Protocols | Cast | Google for Developers](https://developers.google.com/cast/docs/media/streaming_protocols) - Supported streaming protocols
- [GitHub - thibauts/node-castv2](https://github.com/thibauts/node-castv2) - CASTV2 protocol implementation
- [GitHub - thibauts/node-castv2-client](https://github.com/thibauts/node-castv2-client) - Cast client library

### Browser Automation & Video Capture (HIGH Confidence)
- [Mastering Headless Browser Automation: Architecture, Scaling & Browser](https://www.browserless.io/blog/what-is-a-headless-browser-key-features-benefits-and-uses-explained) - Headless browser architecture
- [How to do video recording on headless chrome | by Anchen | Medium](https://medium.com/@anchen.li/how-to-do-video-recording-on-headless-chrome-966e10b1221) - Video recording techniques
- [Puppeteer | Chrome for Developers](https://developer.chrome.com/docs/puppeteer) - Official Puppeteer documentation
- [Using Chrome Devtools Protocol with Puppeteer | by Jarrod Overson | Medium](https://jsoverson.medium.com/using-chrome-devtools-protocol-with-puppeteer-737a1300bac0) - CDP integration

### Session Management (HIGH Confidence)
- [Browser Automation Session Management Guide October 2025](https://www.skyvern.com/blog/browser-automation-session-management/) - Comprehensive session management patterns
- [How do I manage sessions and cookies effectively in Headless Chromium? | WebScraping.AI](https://webscraping.ai/faq/headless-chromium/how-do-i-manage-sessions-and-cookies-effectively-in-headless-chromium) - Cookie persistence strategies
- [Persisting State | Browserless.io](https://docs.browserless.io/browserql/session-management/persisting-state) - State persistence approaches

### FFmpeg & Video Encoding (HIGH Confidence)
- [ffmpeg Documentation](https://ffmpeg.org/ffmpeg.html) - Official FFmpeg documentation
- [How I Built A Video Encoding And Streaming Service | by Aman Kumar Singh | Medium](https://medium.com/@amankumarsingh7702/how-i-built-a-video-processing-pipeline-and-then-set-it-on-fire-e6f6c3527600) - Real-world encoding pipeline
- [How to change video bitrates using FFmpeg | Mux](https://www.mux.com/articles/change-video-bitrate-with-ffmpeg) - Bitrate configuration
- [Tuning Transcode Latency — Xilinx Video SDK 3.0](https://xilinx.github.io/video-sdk/v3.0/tuning_pipeline_latency.html) - Latency optimization techniques
- [Video Encoding Best Practices: 6 Practical Tips | Haivision](https://www.haivision.com/blog/all/video-encoding-best-practices-6-practical-tips-for-optimizing-latency-bandwidth-and-picture-quality/) - Encoding best practices

### Docker & Containerization (HIGH Confidence)
- [GitHub - louisoutin/Docker-Virtual-XVFB-pipewire](https://github.com/louisoutin/Docker-Virtual-XVFB-pipewire) - Xvfb + audio in Docker
- [GitHub - TareqAlqutami/rtmp-hls-server](https://github.com/TareqAlqutami/rtmp-hls-server) - Docker streaming server
- [GitHub - Envek/dockerized-browser-streamer](https://github.com/Envek/dockerized-browser-streamer) - Browser streaming in Docker
- [Running X Client Using Virtual X Server Xvfb - Lei Mao's Log Book](https://leimao.github.io/blog/Running-X-Client-Using-Virtual-X-Server-Xvfb/) - Xvfb setup guide

### Streaming Protocols (HIGH Confidence)
- [HLS, MPEG-DASH, RTMP, and WebRTC - Which Protocol is Right for Your App?](https://getstream.io/blog/protocol-comparison/) - Protocol comparison
- [RTMP vs HLS vs DASH - Streaming Protocols - Linuxhit](https://linuxhit.com/rtmp-vs-hls-vs-dash-streaming-protocols/) - Technical comparison

### API Design & Webhooks (MEDIUM Confidence)
- [What is a webhook and how to use webhooks for real-time video management](https://api.video/blog/tutorials/what-is-a-webhook/) - Webhook patterns for video
- [Webhooks Explained: Optimize Video Streaming Workflows](https://www.fastpix.io/blog/webhooks-explained-optimizing-video-streaming-workflows) - Video workflow automation
- [Video Streaming API Guide: Build Live & VOD in 2025 | Mux](https://www.mux.com/articles/video-streaming-api-how-to-build-live-and-on-demand-video-into-your-app) - API design patterns

---
*Architecture research for: Web-to-video streaming service with Cast protocol integration*
*Researched: 2026-01-15*
