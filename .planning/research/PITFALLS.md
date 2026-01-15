# Pitfalls Research

**Domain:** Web-to-video streaming service with Cast protocol integration
**Researched:** 2026-01-15
**Confidence:** HIGH (Cast/Browser), MEDIUM (Video Encoding), HIGH (Infrastructure)

## Critical Pitfalls

### Pitfall 1: Browser Automation Resource Leaks

**What goes wrong:**
Unclosed browser contexts, orphaned page objects, and zombie Chrome processes accumulate over time, consuming memory and eventually crashing the service. In production, this manifests as gradual memory exhaustion, with "dozens of orphaned Chrome instances" appearing when cleanup fails.

**Why it happens:**
Developers fail to implement proper cleanup in error paths. When exceptions occur during page operations, `page.close()` and `browser.close()` are never called. Additionally, developers often spin up fresh browser instances per request instead of reusing them, and don't implement proper try/finally blocks.

**How to avoid:**
1. Use incognito browser contexts instead of managing full browser lifecycles - "the secret weapon for production Puppeteer deployments"
2. Always wrap operations in try/finally blocks with guaranteed cleanup
3. Reuse browser instances across requests - don't create a new browser per operation
4. Implement connection pooling using libraries like `puppeteer-cluster`
5. Close all pages before calling `browser.close()` to prevent hanging (Windows GPU issue workaround)
6. Monitor Chrome process count per pod: 2-3 processes = healthy, dozens = leak

**Warning signs:**
- Memory usage steadily climbing over hours/days
- Chrome process count increasing beyond 2-3 per pod
- Browser.close() hanging or timing out
- "user data directory is already in use" errors
- Out of memory crashes after extended runtime

**Phase to address:**
Phase 1 (Browser Automation Foundation) - Must establish proper resource management patterns from the start.

**Confidence:** HIGH
**Sources:**
- [The Hidden Cost of Headless Browsers: A Puppeteer Memory Leak Journey](https://medium.com/@matveev.dina/the-hidden-cost-of-headless-browsers-a-puppeteer-memory-leak-journey-027e41291367)
- [Puppeteer in Node.js: Common Mistakes to Avoid](https://blog.appsignal.com/2023/02/08/puppeteer-in-nodejs-common-mistakes-to-avoid.html)
- [Browser.close() doesn't close Chromium if there are open pages](https://github.com/puppeteer/puppeteer/issues/7922)
- [Zombie Chrome child processes in containerized EKS environment](https://github.com/SeleniumHQ/selenium/issues/15632)

---

### Pitfall 2: Docker /dev/shm Exhaustion

**What goes wrong:**
Chrome crashes with out-of-memory errors in Docker containers because the default shared memory size (64MB) is far too small for Chrome's needs. This manifests as cryptic crashes, renderer process failures, and intermittent failures under load.

**Why it happens:**
Docker's default `/dev/shm` is only 64MB, but Chrome uses shared memory extensively for inter-process communication. Most developers don't realize Chrome has special shared memory requirements until it crashes in production.

**How to avoid:**
1. Run containers with `--shm-size=1gb` flag
2. OR launch Chrome with `--disable-dev-shm-usage` flag (writes to /tmp instead)
3. Use `--init` flag (Docker >= 1.13.0) or `dumb-init` to properly reap zombie processes
4. Implement proper process monitoring to detect orphaned Chrome instances

**Warning signs:**
- Chrome crashes with "out of memory" errors despite plenty of system RAM
- Renderer process crashes
- Failures that only appear in Docker but not local development
- Zombie processes accumulating in containers

**Phase to address:**
Phase 1 (Browser Automation Foundation) - Critical Docker configuration must be set before deployment.

**Confidence:** HIGH
**Sources:**
- [Out of memory errors in Headless Chrome 83](https://bugs.chromium.org/p/chromium/issues/detail?id=1085829)
- [Advanced issues when managing Chrome on AWS](https://www.browserless.io/blog/advanced-issues-when-managing-chrome-on-aws)
- [chromedp/docker-headless-shell GitHub](https://github.com/chromedp/docker-headless-shell)

---

### Pitfall 3: Missing Timeouts in Browser Operations

**What goes wrong:**
Pages get stuck loading indefinitely due to network issues, infinite rendering loops, or external resource failures. Without timeouts, requests hang forever, keeping Chrome instances alive and blocking other operations. This causes resource exhaustion and application hangs.

**Why it happens:**
Developers assume pages will always load successfully and don't anticipate network failures, slow third-party scripts, or rendering loops. The default behavior is to wait indefinitely.

**How to avoid:**
1. Set explicit timeouts on all page operations: `page.goto()`, `page.waitForSelector()`, etc.
2. Implement global timeout policies at the browser context level
3. Use watchdog timers for long-running operations
4. Implement circuit breakers for repeatedly failing operations

**Warning signs:**
- Operations hanging indefinitely
- Timeouts only in production, not local testing
- Resource accumulation during network issues
- Requests never completing or timing out

**Phase to address:**
Phase 1 (Browser Automation Foundation) - Essential for production stability.

**Confidence:** HIGH
**Sources:**
- [Puppeteer vs Playwright Performance Comparison](https://www.skyvern.com/blog/puppeteer-vs-playwright-complete-performance-comparison-2025/)
- [Pro Tips for Optimizing Web Automation Using Puppeteer](https://www.browserstack.com/guide/optimize-web-automation-with-puppeteer)

---

### Pitfall 4: Cast Authentication Timing Issues

**What goes wrong:**
Authentication handshake between sender and receiver fails if system time is misaligned by as little as 10 minutes. Chrome will refuse to stream if receiver authentication fails. This causes connection failures that are difficult to diagnose.

**Why it happens:**
Cast protocol uses time-based authentication with tight tolerances. System clock drift, VM clock skew, or incorrect timezone configuration causes cryptographic validation to fail.

**How to avoid:**
1. Implement NTP time synchronization on all nodes
2. Monitor clock drift and alert on discrepancies
3. Validate system time is synchronized during health checks
4. Document time requirements in deployment procedures
5. Implement proper error handling for authentication failures

**Warning signs:**
- Authentication failures with correct credentials
- Failures after system has been running for a while
- Inconsistent failures across different nodes
- Authentication errors in logs mentioning timestamps

**Phase to address:**
Phase 2 (Cast Protocol Integration) - Critical for Cast connectivity.

**Confidence:** HIGH
**Sources:**
- [Discovery Troubleshooting - Google Cast Developers](https://developers.google.com/cast/docs/discovery)
- [Troubleshooting - Cast Android TV Receiver](https://developers.google.com/cast/docs/android_tv_receiver/troubleshooting)

---

### Pitfall 5: Cast CORS Configuration Errors

**What goes wrong:**
Media fails to load on Cast receivers with cryptic CORS errors. Streaming protocols use XMLHttpRequest which is guarded by CORS. Wildcards (`*`) cannot be used for `Access-Control-Allow-Origin` with credentials, causing authentication to fail.

**Why it happens:**
Developers configure CORS for web browsers but don't realize Cast receivers have stricter requirements. Protected media content requires specific domain headers, not wildcards. Required headers include `Content-Type`, `Accept-Encoding`, and `Range` - missing any causes failures.

**How to avoid:**
1. Never use wildcard `*` for Access-Control-Allow-Origin with Cast
2. Always include required headers: Content-Type, Accept-Encoding, Range
3. Configure CORS to allow credentials when needed
4. Test CORS configuration with actual Cast devices, not just browsers
5. Use manifest request handlers to inject custom headers

**Warning signs:**
- Media loads in browser but fails on Cast device
- CORS errors in Cast device logs
- Authentication working but media loading failing
- Manifest or segment request failures

**Phase to address:**
Phase 2 (Cast Protocol Integration) - Must be configured correctly for media playback.

**Confidence:** HIGH
**Sources:**
- [Add Core Features to Your Custom Web Receiver](https://developers.google.com/cast/docs/web_receiver/core_features)
- [Chromecast receiver with custom header - Issue #23](https://github.com/googlecast/CastReceiver/issues/23)
- [Chromecast CORS problem - Kaltura Forum](https://forum.kaltura.org/t/chromecast-cors-problem/10301)

---

### Pitfall 6: Cast Connection Discovery Failures

**What goes wrong:**
Sender apps fail to discover Cast devices, or connections drop unexpectedly. If other apps consistently discover the receiver but your sender doesn't, the problem is in your sender implementation. Network configuration requires sender and Cast device on same WiFi network.

**Why it happens:**
Developers don't implement proper discovery protocols or handle network changes. mDNS/SSDP discovery can be blocked by firewalls or network policies. Apps don't handle WiFi network changes or device sleep/wake cycles.

**How to avoid:**
1. Verify sender and Cast device are on same WiFi network
2. Implement proper SessionManager listeners for connection state changes
3. Handle SENDER_DISCONNECTED events with appropriate maxInactivity timeout
4. Test discovery across different network configurations
5. Implement retry logic with exponential backoff for failed connections

**Warning signs:**
- Discovery works in some network environments but not others
- Other Cast apps discover devices but yours doesn't
- Connections drop when device goes to sleep
- Discovery fails after WiFi network changes

**Phase to address:**
Phase 2 (Cast Protocol Integration) - Core connectivity requirement.

**Confidence:** HIGH
**Sources:**
- [Discovery Troubleshooting - Google Cast Developers](https://developers.google.com/cast/docs/discovery)
- [Error Codes - Google Cast Developers](https://developers.google.com/cast/docs/web_receiver/error_codes)

---

### Pitfall 7: FFmpeg Streaming Bandwidth Bottlenecks

**What goes wrong:**
CPU usage spikes to 100% when using filters during live streaming, causing frame drops and quality degradation. Streaming sources create bandwidth bottlenecks either server-side or client-side, making transcoding significantly slower than file-based encoding.

**Why it happens:**
Developers optimize for file encoding (where input is always available) rather than streaming (where input arrives over network). Network delays compound with encoding delays. Filters and complex processing assume infinite buffer availability.

**How to avoid:**
1. Use hardware acceleration (NVENC for NVIDIA GPUs) when available
2. Optimize for streaming with low-latency flags: `-tune zerolatency`, `-flags low_delay`
3. Use `-fflags +nobuffer+flush_packets` to minimize buffering
4. Set appropriate `-analyzeduration` (default 5 seconds adds latency)
5. Profile encoding pipeline to identify bottlenecks
6. Consider distributed architectures for scaling

**Warning signs:**
- CPU usage at 100% during encoding
- Frame drops in output
- Encoding takes longer than input duration (can't keep up)
- High memory usage with buffering
- Latency increasing over time

**Phase to address:**
Phase 3 (Video Encoding Pipeline) - Critical for streaming performance.

**Confidence:** HIGH
**Sources:**
- [FFmpeg Performance Optimization Guide](https://www.probe.dev/resources/ffmpeg-performance-optimization-guide)
- [Optimize threading+latency of ffmpeg configuration](https://github.com/blakeblackshear/frigate/issues/5459)
- [How To Optimize FFmpeg For Fast Video Encoding](https://www.muvi.com/blogs/optimize-ffmpeg-for-fast-video-encoding/)

---

### Pitfall 8: HLS Keyframe Misalignment

**What goes wrong:**
Adaptive bitrate switching fails or causes stuttering/sync issues because keyframes aren't aligned across different quality levels. Segments have inconsistent sizes and keyframes appear at different timestamps in different renditions.

**Why it happens:**
Developers encode each quality level independently without ensuring keyframes occur at the same timestamps. Default FFmpeg settings allow keyframes at scene changes, causing misalignment. Without `-sc_threshold 0`, GOP sizes vary and keyframes don't align.

**How to avoid:**
1. Set fixed GOP interval: `-g 48 -keyint_min 48` (for 2-second segments at 24fps)
2. Force scene change threshold to 0: `-sc_threshold 0` (critical - prevents automatic keyframes)
3. Use identical encoding parameters across all bitrates except resolution/bitrate
4. Use `-force_key_frames expr:gte(t,n_forced*N)` to force keyframes every N seconds
5. NEVER try to realign existing files - re-encode from scratch

**Warning signs:**
- Stuttering or artifacts when quality switches
- Segments of varying sizes in different renditions
- Player showing sync issues during adaptive switching
- Keyframes at different timestamps across qualities

**Phase to address:**
Phase 3 (Video Encoding Pipeline) - Essential for adaptive streaming quality.

**Confidence:** HIGH
**Sources:**
- [Creating A Production Ready Multi Bitrate HLS VOD stream](https://medium.com/@peer5/creating-a-production-ready-multi-bitrate-hls-vod-stream-dff1e2f1612c)
- [HLS Packaging using FFmpeg Tutorial](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/)
- [Using FFmpeg as a HLS streaming server - Multiple Bitrates](https://www.martin-riedl.de/2018/08/25/using-ffmpeg-as-a-hls-streaming-server-part-3/)

---

### Pitfall 9: FFmpeg Low-Latency Configuration Mistakes

**What goes wrong:**
Streaming latency remains high (10+ seconds) despite targeting low-latency streaming. Default HLS configurations use large segments (6-10 seconds) and excessive buffering, making real-time interaction impossible.

**Why it happens:**
Developers use default FFmpeg settings optimized for quality and buffering, not latency. The default `analyzeduration` adds 5 seconds of latency. Segment duration defaults to values too large for low-latency streaming. Without `zerolatency` tuning, encoder adds 0.5+ seconds of latency.

**How to avoid:**
1. Set segment duration to 1-2 seconds: `-hls_time 1`
2. Use zerolatency tuning: `-tune zerolatency`
3. Add low-latency flags: `-flags low_delay -fflags +nobuffer+flush_packets`
4. Set zero mux delays: `-max_delay 0 -muxdelay 0`
5. Reduce analyzeduration for faster startup
6. Keyframe interval must be ≤ segment duration (each segment needs ≥1 keyframe)
7. Target 2-5 seconds for LL-HLS, ~6 seconds minimum for stable HLS

**Warning signs:**
- End-to-end latency exceeding 10 seconds
- Buffering delays before playback starts
- Slow startup time (first frame displayed)
- Latency increasing over time

**Phase to address:**
Phase 3 (Video Encoding Pipeline) - Required for real-time streaming experience.

**Confidence:** HIGH
**Sources:**
- [Rethinking HLS: Low-Latency Streaming with HLS](https://medium.com/@OvenMediaEngine/rethinking-hls-is-it-possible-to-achieve-low-latency-streaming-with-hls-9d00512b3e61)
- [FFMpeg Reduced Latency HLS - Tebi.io](https://docs.tebi.io/streaming/ffmpeg_rl_hls.html)
- [HLS Low Latency: The Ultimate 2025 Guide](https://www.videosdk.live/developer-hub/hls/hls-low-latency)
- [Achieving Ultra-Low Latency Streaming: Codecs and FFmpeg Examples](https://blog.trixpark.com/achieving-ultra-low-latency-streaming-codecs-and-ffmpeg-examples/)

---

### Pitfall 10: Webhook Queue Saturation

**What goes wrong:**
Sudden influx of webhooks overwhelms server resources (memory, CPU, network), causing slower response times, queue saturation, and eventual system shutdown. Webhook events time out waiting to be added to full queues. Memory exhaustion occurs when broker ingests faster than consumers process.

**Why it happens:**
Developers handle webhooks synchronously, blocking on database writes or external API calls. No rate limiting or backpressure mechanisms. Retry storms occur when system slows down - producers keep retrying, creating avalanche of traffic. No dead-letter queues for failed processing.

**How to avoid:**
1. Implement async webhook handling: verify signature → enqueue → respond immediately
2. Use separate worker pools to process webhook queue
3. Implement backpressure and rate limiting
4. Create dead-letter queues for failures
5. Monitor queue depth and consumer lag
6. Set up circuit breakers for downstream dependencies
7. Design for at-least-once delivery (idempotent processing)

**Warning signs:**
- Webhook response times increasing under load
- Queue depth growing faster than processing rate
- Memory usage spiking with webhook bursts
- Webhook timeout errors from senders
- Consumer lag metrics increasing

**Phase to address:**
Phase 4 (Webhook System) - Critical for handling production load.

**Confidence:** HIGH
**Sources:**
- [Use queue instead of memory queue in webhook send service](https://github.com/go-gitea/gitea/pull/19390)
- [A Beginner's Guide To Handling Webhooks](https://www.vessel.dev/blog/a-beginners-guide-to-handling-webhooks-for-integrations-2cfe2)
- [Webhook Infrastructure Performance Monitoring](https://hookdeck.com/webhooks/guides/webhook-infrastructure-performance-monitoring-scalability-resource)
- [Webhook events are skipped because the queue is full](https://support.atlassian.com/bitbucket-data-center/kb/webhook-events-are-skipped-because-the-queue-is-full/)

---

### Pitfall 11: HDMI CEC Control Conflicts

**What goes wrong:**
Multiple devices connected via CEC fight for control, causing unwanted input switching, power signals, and device wake/sleep conflicts. Chromecast sends unwanted activation signals, automatically switching TV input. When shutting down one device, other CEC devices immediately wake it back up.

**Why it happens:**
CEC is not a fully standardized technology with inconsistent implementations across manufacturers. When Chromecast is connected through an AVR/receiver, multiple devices try to control the same endpoints. CEC Auto creates race conditions between Chromecast, TV, and receiver.

**How to avoid:**
1. Understand that CEC reliability is inherently limited - design for graceful degradation
2. Implement retry logic for CEC commands
3. Consider disabling CEC on external devices while keeping it on AVR/TV
4. Power on source device first, let CEC automatically handle downstream devices
5. Keep firmware updated on all CEC-enabled devices
6. Document CEC limitations for users - it's a known problem
7. Provide manual fallback options when CEC fails

**Warning signs:**
- Chromecast "stealing" input from other devices
- Devices waking up when they should stay off
- Input switching happening automatically when not desired
- Receiver turning on/off unexpectedly
- CEC working initially but failing over time

**Phase to address:**
Phase 5 (HDMI CEC Control) - Set expectations early that CEC is inherently unreliable.

**Confidence:** MEDIUM (CEC is notoriously inconsistent across manufacturers)
**Sources:**
- [Chromecast w GTV is sending unwanted HDMI CEC signal](https://www.googlenestcommunity.com/t5/Streaming/Chromecast-w-GTV-is-sending-unwanted-HDMI-CEC-signal/m-p/296407)
- [2020 Chromecast with Google TV - CEC issues](https://www.avsforum.com/threads/2020-chromecast-with-google-tv-cec-issues.3171135/)
- [HDMI-CEC problems](https://www.avforums.com/threads/hdmi-cec-problems.2335412/)

---

### Pitfall 12: Cast Session Expiration Handling

**What goes wrong:**
Media sessions expire or disconnect, and the application fails to reconnect gracefully. Users lose playback state and must manually restart casting. Session state is lost across app restarts or network interruptions.

**Why it happens:**
Developers don't implement proper session monitoring and reconnection logic. The framework provides automatic reconnection, but apps override or disable it. maxInactivity timeouts aren't configured appropriately. Session state preservation is missing for stream transfer scenarios.

**How to avoid:**
1. Let the framework handle automatic session resumption (SessionManager/GCKSessionManager)
2. Register SessionManagerListener callbacks to handle state transitions
3. Monitor session status changes: connection, suspension, disconnection
4. Implement ReconnectionService (Android) - enabled by default, don't disable
5. For Web: use `requestSessionById(sessionId)` to rejoin existing sessions
6. Configure appropriate maxInactivity timeout (default is usually correct)
7. Implement SESSION_STATE and RESUME_SESSION interceptors for custom state preservation
8. Handle "suspended" state during temporary network loss

**Warning signs:**
- Users losing playback when app backgrounds
- Sessions not resuming after network interruption
- State lost across app restarts
- SENDER_DISCONNECTED events not handled
- Reconnection attempts failing

**Phase to address:**
Phase 2 (Cast Protocol Integration) - Essential for production-quality Cast experience.

**Confidence:** HIGH
**Sources:**
- [Add Core Features to Your Custom Web Receiver](https://developers.google.com/cast/docs/web_receiver/core_features)
- [Integrate Cast Into Your Android App](https://developers.google.com/cast/docs/android_sender/integrate)
- [GCKSessionManager Class Reference](https://developers.google.com/cast/docs/reference/ios/interface_g_c_k_session_manager)
- [Unable to resume the chromecast session - Issue #344](https://github.com/react-native-google-cast/react-native-google-cast/issues/344)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Creating new browser instance per request | Simpler code, no state management | Memory leaks, poor performance, resource exhaustion | Never - always use pooling/contexts |
| Using wildcard CORS headers | Works in development | Breaks Cast authentication, security risks | Never for production Cast apps |
| Synchronous webhook processing | Simple implementation | Queue saturation, poor scalability, cascading failures | Only for MVP with <10 webhooks/hour |
| Skipping FFmpeg zerolatency tuning | Slightly better quality | 10+ seconds latency, poor UX | Only for non-interactive VOD content |
| Default Docker shared memory | No configuration needed | Random Chrome crashes under load | Never - always set --shm-size=1gb |
| Manual resource cleanup (no try/finally) | Saves 2 lines of code | Memory leaks, zombie processes | Never - cleanup must be guaranteed |
| Using scene-change keyframes | Better compression | Breaks adaptive bitrate switching | Never for ABR streaming |
| Ignoring CEC timing issues | Simpler state machine | Unreliable control, user frustration | Document limitations but implement retries |
| Hardcoding segment duration | Quick implementation | Inflexible latency/quality tradeoff | Only for fixed-use-case prototypes |
| Not monitoring Chrome process count | Less infrastructure | Can't detect leaks until crash | Never for production deployment |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Google Cast Protocol | Assuming browser CORS rules apply | Use specific domains, include Range/Accept-Encoding headers, test on actual devices |
| FFmpeg Streaming | Using file-encoding flags for streaming | Use `-tune zerolatency -flags low_delay -fflags +nobuffer+flush_packets` |
| Docker + Chrome | Using default shared memory | Set `--shm-size=1gb` or `--disable-dev-shm-usage` flag |
| Puppeteer/Playwright | Managing browser instances per request | Use incognito contexts within persistent browser instance |
| HLS Adaptive Streaming | Independent encoding per quality | Enforce identical GOP structure with `-sc_threshold 0` |
| Cast Session Management | Implementing custom reconnection logic | Use framework's built-in SessionManager automatic reconnection |
| Webhook Processing | Synchronous handler with DB operations | Async pattern: verify → enqueue → immediate response |
| HDMI CEC | Expecting reliable control | Design for graceful degradation, implement retries, provide manual fallbacks |
| FFmpeg Low Latency | Reducing only segment size | Must also tune keyframe interval, analyzeduration, encoder preset |
| Cast Authentication | Ignoring system clock | Implement NTP sync, validate time in health checks |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No browser instance pooling | Memory grows linearly with requests | Use incognito contexts, reuse browser instances | ~100 concurrent requests |
| Synchronous webhook handling | Response times increase under load | Async queue-based processing | ~50 webhooks/minute |
| Missing FFmpeg hardware acceleration | CPU at 100%, frame drops | Enable NVENC/VAAPI when available | 2+ concurrent HD streams |
| Large FFmpeg segment buffers | Memory usage spikes | Use `-fflags +nobuffer+flush_packets` | Multiple concurrent encodes |
| No Chrome process monitoring | Gradual memory leak | Alert on >3 Chrome processes per pod | After hours/days runtime |
| Single-threaded encoding | Can't use multiple cores | Use `-threads N` appropriate for CPU | HD+ video at high quality |
| Missing backpressure in queues | Memory exhaustion | Implement queue depth limits and rejection | Traffic bursts >10x normal |
| No connection pooling | Socket exhaustion | Reuse connections to external services | ~1000 requests/minute |
| Unbounded retry storms | Cascading failures | Exponential backoff, circuit breakers | Service degradation |
| Missing webhook idempotency | Duplicate processing | Design for at-least-once delivery | Retry storms |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Wildcard CORS with credentials | Authentication bypass on Cast | Use specific origin domains, never `*` with credentials |
| Exposing webhook URLs without verification | Fake/malicious webhooks | Always verify webhook signatures before processing |
| Running Chrome without sandboxing | Container escape, privilege escalation | Use `--no-sandbox` only when absolutely necessary, document risk |
| Storing Cast session IDs in logs | Session hijacking | Sanitize logs, use secure session management |
| Not rate-limiting webhook endpoints | DoS, resource exhaustion | Implement rate limiting at multiple levels (IP, signature, queue) |
| Trusting client-provided URLs | SSRF attacks via browser automation | Validate/whitelist URLs before automation |
| Exposing FFmpeg input paths | File system access, info disclosure | Validate input paths, use chroot/containers |
| Missing authentication on Cast receivers | Unauthorized casting, content injection | Implement proper sender authentication |
| Leaking Chrome debugging ports | Remote browser control | Bind debugging to localhost only, firewall properly |
| Not sanitizing webhook payloads | Injection attacks | Validate and sanitize all webhook data |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No feedback during encoding | Users think system is frozen | Stream progress updates, show encoding status |
| No graceful degradation when CEC fails | Users frustrated with unreliable control | Provide manual fallback controls, clear status |
| Long startup latency | Users wait 10+ seconds for playback | Optimize for low-latency with proper FFmpeg flags |
| Cast session lost without warning | Playback stops unexpectedly | Implement reconnection with user notification |
| No error messages on Cast failure | Users don't know what went wrong | Surface Cast errors with actionable messages |
| Webhook failures invisible | Users unaware system isn't working | Status dashboard, webhook delivery confirmations |
| Quality switching causes buffering | Stuttering playback experience | Ensure keyframe alignment for smooth ABR switching |
| No timeout feedback | Operations hang indefinitely | Show timeout warnings, allow cancellation |
| Cast device not discoverable | Users can't figure out connection | Clear discovery status, troubleshooting hints |
| Memory leak causes gradual slowdown | Performance degrades mysteriously | Monitor and restart before problems visible |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Browser Automation:** Often missing try/finally cleanup — verify zombie Chrome processes don't accumulate over 24 hours
- [ ] **Docker Chrome Setup:** Often missing --shm-size config — verify Chrome doesn't crash under load with default 64MB
- [ ] **FFmpeg Encoding:** Often missing zerolatency tuning — verify actual end-to-end latency with stopwatch
- [ ] **HLS Adaptive Streaming:** Often missing sc_threshold 0 — verify keyframes align across qualities with ffprobe
- [ ] **Webhook Handling:** Often missing async queue processing — verify system handles 10x traffic burst
- [ ] **Cast CORS:** Often using wildcards — verify media loads on actual Cast device, not just browser
- [ ] **Resource Monitoring:** Often missing Chrome process counting — verify alerts trigger on process leaks
- [ ] **Timeout Configuration:** Often missing on page operations — verify hung pages don't block system
- [ ] **Session Reconnection:** Often disabled framework auto-reconnect — verify session survives network interruption
- [ ] **CEC Control:** Often assuming reliability — verify graceful fallback when CEC fails
- [ ] **Error Handling:** Often missing error paths in cleanup — verify resources freed even when exceptions occur
- [ ] **Dead Letter Queues:** Often missing for webhooks — verify failed webhooks don't disappear silently

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Browser resource leaks | LOW | Restart service, implement process monitoring to catch early, add automated restarts |
| Docker /dev/shm exhaustion | LOW | Update Docker config with --shm-size=1gb, restart containers |
| Missing timeouts | LOW | Add timeout wrappers to existing operations, no major refactoring needed |
| Cast authentication timing | LOW | Configure NTP sync, restart services, verify time with `date` command |
| CORS misconfiguration | LOW | Update CORS headers to specific domains, redeploy receiver |
| HLS keyframe misalignment | HIGH | Must re-encode all video assets from scratch with proper flags |
| Webhook queue saturation | MEDIUM | Scale consumers, implement backpressure, may require architecture changes |
| FFmpeg latency issues | MEDIUM | Reconfigure encoding pipeline, may need to regenerate content |
| Cast session handling | MEDIUM | Refactor to use framework SessionManager, test reconnection scenarios |
| CEC conflicts | MEDIUM | Document workarounds, provide manual controls, can't fully "fix" CEC |
| Zombie Chrome processes | LOW | Implement init system, add process cleanup, restart pods |
| Security issues (CORS wildcard) | LOW | Update configuration, redeploy, verify with testing |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Browser resource leaks | Phase 1 (Browser Automation) | Monitor Chrome process count, run 24hr load test |
| Docker /dev/shm exhaustion | Phase 1 (Browser Automation) | Verify --shm-size in Docker config, test under load |
| Missing timeouts | Phase 1 (Browser Automation) | Verify all page operations have explicit timeouts |
| Cast authentication timing | Phase 2 (Cast Protocol) | Verify NTP configured, test with clock skew |
| CORS misconfiguration | Phase 2 (Cast Protocol) | Test media loading on actual Cast device |
| Cast connection discovery | Phase 2 (Cast Protocol) | Test discovery across different networks |
| Cast session handling | Phase 2 (Cast Protocol) | Test reconnection after network interruption |
| FFmpeg bandwidth bottlenecks | Phase 3 (Video Encoding) | Monitor CPU usage, verify real-time encoding |
| HLS keyframe misalignment | Phase 3 (Video Encoding) | Verify with ffprobe that keyframes align |
| FFmpeg low-latency config | Phase 3 (Video Encoding) | Measure end-to-end latency with stopwatch |
| Webhook queue saturation | Phase 4 (Webhook System) | Load test with 10x expected traffic |
| HDMI CEC conflicts | Phase 5 (HDMI CEC Control) | Test with multiple devices, verify fallbacks |

## Sources

### Cast Protocol & Chromecast
- [Google Cast Developers - Discovery Troubleshooting](https://developers.google.com/cast/docs/discovery)
- [Google Cast Developers - Error Codes](https://developers.google.com/cast/docs/web_receiver/error_codes)
- [Google Cast Developers - Add Core Features to Your Custom Web Receiver](https://developers.google.com/cast/docs/web_receiver/core_features)
- [Google Cast Developers - Integrate Cast Into Your Android App](https://developers.google.com/cast/docs/android_sender/integrate)
- [GitHub - googlecast/CastReceiver Issue #23: Chromecast receiver with custom header](https://github.com/googlecast/CastReceiver/issues/23)
- [Kaltura Forum - Chromecast CORS problem](https://forum.kaltura.org/t/chromecast-cors-problem/10301)
- [GitHub - react-native-google-cast Issue #344: Unable to resume the chromecast session](https://github.com/react-native-google-cast/react-native-google-cast/issues/344)

### Browser Automation (Puppeteer/Playwright)
- [Medium - The Hidden Cost of Headless Browsers: A Puppeteer Memory Leak Journey](https://medium.com/@matveev.dina/the-hidden-cost-of-headless-browsers-a-puppeteer-memory-leak-journey-027e41291367)
- [AppSignal Blog - Puppeteer in Node.js: Common Mistakes to Avoid](https://blog.appsignal.com/2023/02/08/puppeteer-in-nodejs-common-mistakes-to-avoid.html)
- [GitHub - puppeteer/puppeteer Issue #7922: Browser.close() doesn't close Chromium if there are open pages](https://github.com/puppeteer/puppeteer/issues/7922)
- [GitHub - puppeteer/puppeteer Issue #11627: Closing browser contexts can leave dangling service workers](https://github.com/puppeteer/puppeteer/issues/11627)
- [Puppeteer vs Playwright Performance Comparison 2025](https://www.skyvern.com/blog/puppeteer-vs-playwright-complete-performance-comparison-2025/)
- [BrowserStack - Pro Tips for Optimizing Web Automation Using Puppeteer](https://www.browserstack.com/guide/optimize-web-automation-with-puppeteer)
- [Browserless - Memory Leak: How to Find, Fix & Prevent Them](https://www.browserless.io/blog/memory-leak-how-to-find-fix-prevent-them)

### Docker + Headless Chrome
- [Chromium Bugs - Out of memory errors in Headless Chrome 83](https://bugs.chromium.org/p/chromium/issues/detail?id=1085829)
- [Browserless - Advanced issues when managing Chrome on AWS](https://www.browserless.io/blog/advanced-issues-when-managing-chrome-on-aws)
- [GitHub - chromedp/docker-headless-shell](https://github.com/chromedp/docker-headless-shell)
- [GitHub - SeleniumHQ/selenium Issue #15632: Zombie Chrome child processes in containerized EKS environment](https://github.com/SeleniumHQ/selenium/issues/15632)

### FFmpeg & Video Encoding
- [Probe.dev - FFmpeg Performance Optimization Guide](https://www.probe.dev/resources/ffmpeg-performance-optimization-guide)
- [Muvi - How To Optimize FFmpeg For Fast Video Encoding](https://www.muvi.com/blogs/optimize-ffmpeg-for-fast-video-encoding/)
- [GitHub - blakeblackshear/frigate Issue #5459: Optimize threading+latency of ffmpeg configuration](https://github.com/blakeblackshear/frigate/issues/5459)
- [Medium - Rethinking HLS: Is it Possible to Achieve Low-Latency Streaming with HLS?](https://medium.com/@OvenMediaEngine/rethinking-hls-is-it-possible-to-achieve-low-latency-streaming-with-hls-9d00512b3e61)
- [Tebi.io - FFMpeg Reduced Latency HLS](https://docs.tebi.io/streaming/ffmpeg_rl_hls.html)
- [VideoSDK - HLS Low Latency: The Ultimate 2025 Guide](https://www.videosdk.live/developer-hub/hls/hls-low-latency)
- [Trixpark Blog - Achieving Ultra-Low Latency Streaming: Codecs and FFmpeg Examples](https://blog.trixpark.com/achieving-ultra-low-latency-streaming-codecs-and-ffmpeg-examples/)

### HLS & Adaptive Bitrate Streaming
- [Medium - Creating A Production Ready Multi Bitrate HLS VOD stream](https://medium.com/@peer5/creating-a-production-ready-multi-bitrate-hls-vod-stream-dff1e2f1612c)
- [OTTVerse - HLS Packaging using FFmpeg - Easy Step-by-Step Tutorial](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/)
- [Martin Riedl - Using FFmpeg as a HLS streaming server (Part 3) – Multiple Bitrates](https://www.martin-riedl.de/2018/08/25/using-ffmpeg-as-a-hls-streaming-server-part-3/)
- [Medium - Adaptive bitrate streaming HLS VOD service in NodeJS](https://medium.com/sharma02gaurav/adaptive-bitrate-streaming-hls-vod-service-in-nodejs-8df0d91d2eb4)

### Webhook Processing
- [GitHub - go-gitea/gitea PR #19390: Use queue instead of memory queue in webhook send service](https://github.com/go-gitea/gitea/pull/19390)
- [Vessel - A Beginner's Guide To Handling Webhooks for Integrations](https://www.vessel.dev/blog/a-beginners-guide-to-handling-webhooks-for-integrations-2cfe2)
- [Hookdeck - Webhook Infrastructure Performance Monitoring, Scalability Tuning and Resource Estimation](https://hookdeck.com/webhooks/guides/webhook-infrastructure-performance-monitoring-scalability-resource)
- [Atlassian Support - Webhook events are skipped because the queue is full](https://support.atlassian.com/bitbucket-data-center/kb/webhook-events-are-skipped-because-the-queue-is-full/)

### HDMI CEC Issues
- [Google Nest Community - Chromecast w GTV is sending unwanted HDMI CEC signal](https://www.googlenestcommunity.com/t5/Streaming/Chromecast-w-GTV-is-sending-unwanted-HDMI-CEC-signal/m-p/296407)
- [AVS Forum - 2020 Chromecast with Google TV - CEC issues](https://www.avsforum.com/threads/2020-chromecast-with-google-tv-cec-issues.3171135/)
- [AVForums - HDMI CEC problems](https://www.avforums.com/threads/hdmi-cec-problems.2335412/)

---
*Pitfalls research for: Web-to-video streaming service with Cast protocol integration*
*Researched: 2026-01-15*
