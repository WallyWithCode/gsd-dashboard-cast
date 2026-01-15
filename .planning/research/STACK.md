# Stack Research

**Domain:** Web-to-video streaming service with Cast protocol integration
**Researched:** 2026-01-15
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Playwright | v1.57.0+ | Headless browser automation | Official Docker support, cross-browser capability (Chromium/Firefox/WebKit), superior Docker integration vs Puppeteer, async-first design. Better suited for 2025+ production deployments. |
| FFmpeg | 7.x (latest stable) | Video encoding and streaming | Industry standard for video processing, comprehensive codec support (H.264/HEVC/VP8/VP9), hardware acceleration (NVENC/VAAPI), proven Docker deployment patterns. |
| FastAPI | 3.x (async) | Webhook server framework | 3-5x better performance than Flask (20,000+ rps vs 4,000-5,000 rps), native async/await support, 40% adoption increase in 2025, ideal for high-concurrency webhook processing. |
| pychromecast | 14.0.9+ | Cast protocol implementation | Official Home Assistant library, Python 3.11+ support, maintained by home-assistant-libs, production-ready mDNS discovery, TCP bridging capability. |
| Python | 3.11+ | Primary runtime | Required by pychromecast, excellent async support, mature ecosystem for video/network operations. |
| Xvfb | Latest (via Ubuntu) | Virtual display server | Standard solution for headless browser rendering in Docker, battle-tested performance, direct FFmpeg integration capability. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | Latest | ASGI server for FastAPI | Production deployment - handles async requests efficiently, pairs with FastAPI for optimal performance |
| pyCEC | 0.5.2+ | HDMI CEC control | HDMI auto-wake functionality - provides object API to libcec, TCP bridge support, Home Assistant integration |
| VidGear | Latest | Video processing framework | Advanced video operations - asyncio-based, wraps FFmpeg/OpenCV, optimized for real-time streaming |
| aiortc | Latest | WebRTC support | If adding browser-to-browser streaming - Pythonic WebRTC with asyncio integration |
| python-dotenv | Latest | Environment configuration | Secure credential management for authentication tokens, API keys |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Docker Compose | Multi-container orchestration | Essential for coordinating browser, video encoder, webhook server components |
| playwright/docker | Official Playwright containers | Use `mcr.microsoft.com/playwright:v1.57.0-noble` - includes Ubuntu 24.04 LTS with all dependencies |
| jrottenberg/ffmpeg | Production FFmpeg images | Multiple variants (Ubuntu/Alpine/NVIDIA) - choose ubuntu2404-vaapi for Intel/AMD hardware accel |

## Installation

### Docker Base Images
```dockerfile
# Primary runtime
FROM mcr.microsoft.com/playwright:v1.57.0-noble

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    ffmpeg \
    xvfb \
    libcec6 \
    cec-utils \
    pulseaudio

# Python packages
COPY requirements.txt .
RUN pip3 install -r requirements.txt
```

### Python Requirements
```txt
# Core framework
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pychromecast>=14.0.9

# Video processing
vidgear
Pillow

# CEC control (optional - for HDMI auto-wake)
pyCEC>=0.5.2

# Authentication & utilities
httpx
python-dotenv
pydantic>=2.0
```

### Playwright Python
```bash
# Install Playwright for Python
pip install playwright
playwright install chromium  # Or install in Dockerfile
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Playwright | Puppeteer | If you need Chrome-specific features, advanced stealth capabilities, or slightly faster performance for very short scripts (30% faster). Puppeteer more mature but requires more manual Docker setup. |
| FastAPI | Flask | Simple webhook receivers with <1000 rps requirements where async complexity isn't justified. Flask has broader ecosystem but 5x slower performance. |
| pychromecast | node-castv2 | If building in Node.js ecosystem. node-castv2-client provides similar functionality but requires JavaScript runtime. Less maintained than pychromecast. |
| FFmpeg | GStreamer | Complex pipeline requirements with plugin architecture needs. GStreamer more modular but steeper learning curve and less Docker-optimized images. |
| Python | Node.js | If team expertise is JavaScript-heavy. Node with Puppeteer + node-castv2 viable but loses Home Assistant pychromecast integration benefits. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Puppeteer (for this project) | Requires more manual Docker configuration, Chromium-only (no cross-browser fallback), less optimal for containerized environments in 2025 | Playwright - official Docker images, better container support, cross-browser capability |
| Selenium | Significantly slower than modern alternatives, heavy resource usage, outdated architecture for headless automation | Playwright or Puppeteer - modern async APIs, better performance |
| cec-client CLI | Limited programmatic control, subprocess overhead, harder error handling | pyCEC - Python object API, TCP bridge capability, better Home Assistant integration |
| Synchronous Python frameworks | Cannot handle concurrent webhooks efficiently, blocks on I/O operations | FastAPI with async/await - native concurrency support |
| Alpine Linux base | Missing hardware acceleration libraries (VAAPI), compilation required for many libs, potential compatibility issues | Ubuntu 24.04 (Noble) - better hardware support, pre-built packages |

## Stack Patterns by Variant

### High-Performance Production (Recommended)
**If deploying to cloud/VPS with modern CPU:**
- Base: `mcr.microsoft.com/playwright:v1.57.0-noble`
- FastAPI with uvicorn (multiple workers)
- FFmpeg with software encoding (H.264 High Profile)
- Xvfb with 1920x1080x24 virtual display
- Because: Best balance of compatibility, performance, and resource usage. Software encoding works everywhere.

### Hardware-Accelerated Production
**If deploying to dedicated hardware with NVIDIA GPU:**
- Base: Ubuntu 22.04 with NVIDIA container runtime
- FFmpeg with NVENC hardware encoding
- Playwright separate from encoding container
- Multiple quality tiers (1080p60, 720p30, 480p30)
- Because: 3-10x faster encoding, enables multiple concurrent streams, but requires GPU access and specific hardware.

### Development/Testing
**If running local development:**
- Docker Compose with hot-reload
- FastAPI with `--reload` flag
- Single quality preset (720p30)
- Persistent cookie/session storage via volumes
- Because: Fast iteration, easier debugging, minimal resource usage.

### Home Assistant Integration
**If primary use is Home Assistant automation:**
- FastAPI webhook receiver on standard HA port
- pychromecast with mDNS discovery
- pyCEC TCP bridge for remote CEC control
- Environment variable configuration via HA secrets
- Because: Seamless HA integration, follows HA security patterns, supports HA automations naturally.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Playwright v1.57.0 | Python 3.8-3.12 | Pin to exact version to match Docker image browsers |
| pychromecast 14.x | Python 3.11+ | Requires Python 3.11+ as of recent versions |
| FastAPI 0.100+ | Pydantic 2.x | Breaking changes between Pydantic v1 and v2 |
| FFmpeg 7.x | H.264 High Profile 4.2 | Required for Chromecast 1080p60 compatibility |
| pyCEC 0.5.2 | libcec 6.x | Must have libcec6 system library installed |
| VidGear | FFmpeg 4.4+ | Requires FFmpeg in system PATH |
| Ubuntu Noble 24.04 | Playwright 1.57+ | Official support as of Playwright 1.57 |

## Docker-Specific Considerations

### Display Configuration
```bash
# Start Xvfb in container
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

### Volume Mounts
```yaml
volumes:
  # Persistent browser sessions/cookies
  - ./data/sessions:/app/sessions
  # FFmpeg output cache
  - ./data/streams:/app/streams
  # Configuration
  - ./config:/app/config:ro
```

### Network Configuration
- Host network mode recommended for mDNS (Cast device discovery)
- Alternative: macvlan network for proper multicast support
- Expose webhook port (default: 8000)

### Security Hardening
- Run as non-root user in container
- Use seccomp profile for browser (especially if rendering untrusted content)
- Treat webhook IDs as secrets (use UUIDs, not sequential IDs)
- Enable local_only for webhooks if no internet access needed
- Always use HTTPS in production (reverse proxy recommended)

### Resource Limits
```yaml
# Recommended Docker resource limits
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
    reservations:
      cpus: '2.0'
      memory: 2G
```

### Performance Optimization
- Use tmpfs for Xvfb shared memory: `--shm-size=2g`
- Direct FFmpeg buffer access to Xvfb (avoid intermediate files)
- Pre-launch browser instance (warm start) for faster webhook response
- Connection pooling for Cast device communication
- Rate limiting on webhook endpoints

## Media Format Requirements

### Chromecast Compatibility
| Container | Video Codec | Audio Codec | Max Resolution |
|-----------|-------------|-------------|----------------|
| MP4 | H.264 High Profile L4.2 | AAC-LC/HE-AAC | 1080p60 |
| WebM | VP8 | Vorbis | 4K30 |
| WebM | VP9 | Vorbis/Opus | 4K60 |
| MP4 | HEVC/H.265 Main L5.1 | AAC | 4K60 |

### Recommended Encoding Settings
```bash
# H.264 High Profile (best compatibility)
ffmpeg -f x11grab -i :99 \
  -c:v libx264 -profile:v high -level 4.2 \
  -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -f mp4 -movflags +faststart output.mp4

# VP9 (better compression, 4K support)
ffmpeg -f x11grab -i :99 \
  -c:v libvpx-vp9 -b:v 2M \
  -c:a libopus -b:a 128k \
  -f webm output.webm
```

## Authentication Patterns

### Cookie-Based Session Persistence
```python
# Save cookies after login
await page.context.storage_state(path="auth.json")

# Load cookies for subsequent requests
context = await browser.new_context(storage_state="auth.json")
```

### Security Considerations
- Session tokens typically expire in 30-60 minutes (refresh regularly)
- Encrypt stored cookies at rest
- Use separate browser contexts per user/session
- Implement userDataDir persistence for long-lived sessions
- Validate webhook payloads to prevent injection attacks

## Sources

### Official Documentation (HIGH confidence)
- [Playwright Docker Official Docs](https://playwright.dev/docs/docker) - Docker deployment patterns
- [Playwright Python Docker Docs](https://playwright.dev/python/docs/docker) - Python-specific setup
- [FFmpeg Official Documentation](https://ffmpeg.org/ffmpeg.html) - Encoding parameters
- [FFmpeg Codecs Documentation](https://ffmpeg.org/ffmpeg-codecs.html) - Codec specifications
- [Google Cast Supported Media](https://developers.google.com/cast/docs/media) - Official format requirements
- [Home Assistant Automation Triggers](https://www.home-assistant.io/docs/automation/trigger/) - Webhook setup
- [pychromecast GitHub Repository](https://github.com/home-assistant-libs/pychromecast) - Official library docs
- [FastAPI Official Site](https://www.jetbrains.com/pycharm/2025/02/django-flask-fastapi/) - Framework comparison

### Technical Comparisons (HIGH confidence)
- [Playwright vs Puppeteer 2025 Comparison](https://www.browserstack.com/guide/playwright-vs-puppeteer) - BrowserStack analysis
- [FastAPI vs Flask 2025 Performance](https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison) - Performance benchmarks
- [FFmpeg Docker Images Comparison](https://github.com/jrottenberg/ffmpeg) - jrottenberg/ffmpeg variants
- [Playwright Performance Comparison](https://www.skyvern.com/blog/puppeteer-vs-playwright-complete-performance-comparison-2025/) - Speed test results

### Implementation Guides (MEDIUM-HIGH confidence)
- [Home Assistant Webhook Best Practices](https://www.nabucasa.com/config/webhooks/) - Nabu Casa official guide
- [Puppeteer Cookie Management](https://www.webshare.io/academy-article/puppeteer-cookies) - Session persistence patterns
- [Docker Xvfb Performance Tips](https://minerl.readthedocs.io/en/latest/notes/performance-tips.html) - Optimization techniques
- [FFmpeg Live Streaming 2025](https://www.dacast.com/blog/how-to-broadcast-live-stream-using-ffmpeg/) - Broadcasting best practices
- [Python Asyncio Performance 2025](https://www.nucamp.co/blog/coding-bootcamp-backend-with-python-2025-python-in-the-backend-in-2025-leveraging-asyncio-and-fastapi-for-highperformance-systems) - Async patterns

### Specialized Libraries (MEDIUM confidence)
- [pyCEC PyPI](https://pypi.org/project/pyCEC/) - CEC control library
- [VidGear GitHub](https://github.com/abhiTronix/vidgear) - Video processing framework
- [node-castv2 GitHub](https://github.com/thibauts/node-castv2) - Alternative Cast implementation
- [dockerized-browser-streamer](https://github.com/Envek/dockerized-browser-streamer) - Reference implementation

### Community Resources (MEDIUM confidence)
- [Home Assistant HDMI CEC Integration](https://www.home-assistant.io/integrations/hdmi_cec/) - CEC setup guide
- [Better Stack Playwright vs Puppeteer](https://betterstack.com/community/comparisons/playwright-vs-puppeteer/) - Detailed comparison
- [Microsoft Playwright Docker Hub](https://hub.docker.com/r/microsoft/playwright) - Container registry
- [LinuxServer FFmpeg Image](https://hub.docker.com/r/linuxserver/ffmpeg) - Alternative FFmpeg container

---
*Stack research for: Web-to-video streaming service with Cast protocol integration*
*Researched: 2026-01-15*
*Focus: Docker deployment, Home Assistant webhooks, Cast streaming, authentication handling*
