# Requirements: Dashboard Cast Service v1.1

**Defined:** 2026-01-17
**Core Value:** Complete the Cast playback pipeline with dual-mode streaming for both dashboard reliability and camera feed low-latency.

## v1.1 Requirements

Requirements for v1.1 Cast Media Playback milestone. Each maps to roadmap phases.

### HTTP Streaming

- [x] **STRM-01**: HTTP endpoints serve video streams to Cast device via FastAPI
- [x] **STRM-02**: Service supports dual-mode streaming: HLS (buffered) and fMP4 (low-latency)
- [x] **STRM-03**: Per-request mode selection via webhook `mode` parameter
- [x] **STRM-04**: HLS playlists served with `application/vnd.apple.mpegurl` content type
- [x] **STRM-05**: Video segments served with proper MIME types (video/MP2T, video/mp4)
- [x] **STRM-06**: CORS headers configured for Cast device access

### Cast Playback

- [x] **CAST-01**: `media_controller.play_media()` displays HTTP stream on TV
- [x] **CAST-02**: Correct `stream_type` parameter used (BUFFERED for HLS, LIVE for fMP4)
- [x] **CAST-03**: Correct `content_type` passed to play_media based on mode

### Network Configuration

- [x] **NET-01**: Auto-detect host IP for Cast-accessible stream URL
- [x] **NET-02**: Stream URL accessible from Cast device's network

### FFmpeg Pipeline

- [x] **ENC-01**: HLS output mode generates MPEG-TS segments with playlist
- [x] **ENC-02**: fMP4 output mode generates fragmented MP4 stream
- [x] **ENC-03**: H.264 High Profile Level 4.1 for universal Cast compatibility
- [x] **ENC-04**: AAC audio encoding for Cast compatibility

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Network Configuration

- **NET-03**: `STREAM_HOST_IP` env var for manual override
- **NET-04**: `STREAM_PORT` env var for separate streaming port

### FFmpeg Pipeline

- **ENC-05**: Configurable keyframe interval per mode
- **ENC-06**: Mode-specific FFmpeg presets (veryfast for HLS, ultrafast for fMP4)

### Cast Playback

- **CAST-04**: Mode-specific stream configuration (different settings for dashboard vs camera)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Custom Cast receiver app | High complexity, default media receiver works for v1.1 |
| Adaptive bitrate streaming | Single quality per stream sufficient for v1.1 |
| DASH manifest support | HLS and direct fMP4 cover all use cases |
| Hardware encoding (NVENC/VAAPI) | Deferred to v2, software encoding works everywhere |
| Multiple simultaneous streams | Single stream target for v1.1 |

## Traceability

Which phases cover which requirements. Updated by create-roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STRM-01 | Phase 6 | Complete |
| STRM-02 | Phase 6 | Complete |
| STRM-03 | Phase 7 | Complete |
| STRM-04 | Phase 6 | Complete |
| STRM-05 | Phase 6 | Complete |
| STRM-06 | Phase 6 | Complete |
| CAST-01 | Phase 8 | Complete |
| CAST-02 | Phase 8 | Complete |
| CAST-03 | Phase 8 | Complete |
| NET-01 | Phase 6 | Complete |
| NET-02 | Phase 6 | Complete |
| ENC-01 | Phase 7 | Complete |
| ENC-02 | Phase 7 | Complete |
| ENC-03 | Phase 7 | Complete |
| ENC-04 | Phase 7 | Complete |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 15 ✓
- Unmapped: 0

---
*Requirements defined: 2026-01-17*
*Last updated: 2026-01-18 after Phase 8 completion*
