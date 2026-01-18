# Requirements: Dashboard Cast Service v2.0

**Defined:** 2026-01-18
**Core Value:** Seamless webhook-triggered casting of authenticated web dashboards to Android TV, enabling Home Assistant automations to display contextual information on demand.

## v2.0 Requirements

Requirements for v2.0 Stability and Hardware Acceleration milestone. Each maps to roadmap phases.

### HLS Streaming Stability

- [ ] **HLS-01**: HLS streams play indefinitely without freezing (fix 6-second freeze bug)
- [ ] **HLS-02**: HLS buffer window configured for 40-60s buffer (20-30 segments)
- [ ] **HLS-03**: EVENT playlist type or omit_endlist flag enabled for continuous streaming
- [ ] **HLS-04**: GOP keyframes aligned with segment duration to prevent stuttering
- [ ] **HLS-05**: Startup cleanup removes stale HLS segments from previous sessions

### Low-Latency Mode

- [ ] **FMP4-01**: fMP4 mode plays without freezing on Cast device (validation testing)
- [ ] **FMP4-02**: CMAF fragmentation compliance verified (movflags correct)
- [ ] **FMP4-03**: Range request support validated with Cast device
- [ ] **FMP4-04**: MIME type and CORS headers validated for fMP4 streaming

### Process Lifecycle Management

- [ ] **PROC-01**: Cast session state monitoring detects device-initiated stops
- [ ] **PROC-02**: pychromecast MediaStatusListener monitors IDLE player state transitions
- [ ] **PROC-03**: Process registry tracks all active FFmpeg PIDs
- [ ] **PROC-04**: FFmpeg processes automatically cleaned up when cast stops from device
- [ ] **PROC-05**: Timeout escalation cleanup pattern (stdin 'q' → SIGTERM → SIGKILL)
- [ ] **PROC-06**: Signal handlers for Docker SIGTERM enable graceful shutdown
- [ ] **PROC-07**: Process tree termination with psutil prevents orphaned child processes

### Hardware Acceleration

- [ ] **HWAC-01**: Intel QuickSync h264_qsv encoder support implemented
- [ ] **HWAC-02**: Graceful fallback to software encoding if QuickSync unavailable
- [ ] **HWAC-03**: Runtime hardware detection with vainfo verification
- [ ] **HWAC-04**: QuickSync achieves 80-90% CPU reduction per stream vs software encoding
- [ ] **HWAC-05**: Proxmox GPU passthrough documentation created (IOMMU config, /dev/dri access)
- [ ] **HWAC-06**: Docker render GID configured to match host for /dev/dri access
- [ ] **HWAC-07**: FFmpeg 7.0+ with OneVPL support for Gen 12+ Intel GPUs

### Operational Robustness

- [ ] **OPER-01**: Health check endpoint reports QuickSync availability status
- [ ] **OPER-02**: Process monitoring background task detects orphaned FFmpeg processes
- [ ] **OPER-03**: Structured logging for FFmpeg lifecycle events (start, stop, error, cleanup)
- [ ] **OPER-04**: Service degrades gracefully when hardware acceleration unavailable

## v2.1+ Requirements

Deferred to future releases. Tracked but not in current roadmap.

### Advanced Streaming

- **HLS-06**: Adaptive bitrate streaming with multiple quality variants
- **HLS-07**: Network jitter handling with dynamic buffer adjustment
- **HLS-08**: Custom segment naming for better cache control

### Hardware Support

- **HWAC-08**: NVIDIA NVENC hardware acceleration support
- **HWAC-09**: AMD VAAPI hardware acceleration support
- **HWAC-10**: Automatic driver selection (iHD vs i965) based on CPU generation

### Monitoring

- **OPER-05**: Prometheus metrics endpoint for monitoring
- **OPER-06**: FFmpeg crash recovery with automatic restart
- **OPER-07**: Resource usage limits per stream (CPU, memory caps)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multiple simultaneous streams per device | Current architecture supports single device only, multi-stream adds complexity without clear user value |
| Automatic quality selection | Hardware acceleration provides sufficient performance, adaptive bitrate deferred to v2.1+ |
| Custom Cast receiver app | 10-minute timeout acceptable for MVP, custom receiver adds $5 cost + deployment complexity |
| Real-time transcoding | Dashboards are web content (already rendered), not video files requiring transcode |
| Mobile/desktop casting | Android TV Cast protocol only, different protocols for other platforms |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HLS-01 | TBD | Pending |
| HLS-02 | TBD | Pending |
| HLS-03 | TBD | Pending |
| HLS-04 | TBD | Pending |
| HLS-05 | TBD | Pending |
| FMP4-01 | TBD | Pending |
| FMP4-02 | TBD | Pending |
| FMP4-03 | TBD | Pending |
| FMP4-04 | TBD | Pending |
| PROC-01 | TBD | Pending |
| PROC-02 | TBD | Pending |
| PROC-03 | TBD | Pending |
| PROC-04 | TBD | Pending |
| PROC-05 | TBD | Pending |
| PROC-06 | TBD | Pending |
| PROC-07 | TBD | Pending |
| HWAC-01 | TBD | Pending |
| HWAC-02 | TBD | Pending |
| HWAC-03 | TBD | Pending |
| HWAC-04 | TBD | Pending |
| HWAC-05 | TBD | Pending |
| HWAC-06 | TBD | Pending |
| HWAC-07 | TBD | Pending |
| OPER-01 | TBD | Pending |
| OPER-02 | TBD | Pending |
| OPER-03 | TBD | Pending |
| OPER-04 | TBD | Pending |

**Coverage:**
- v2.0 requirements: 29 total
- Mapped to phases: 0 (awaiting roadmap)
- Unmapped: 29 ⚠️

---
*Requirements defined: 2026-01-18*
*Last updated: 2026-01-18 after initial definition*
