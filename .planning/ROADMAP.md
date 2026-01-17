# Roadmap: Dashboard Cast Service

## Milestones

- ✅ **v1.0 MVP** - Phases 1-5 (shipped 2026-01-15)
- 🚧 **v1.1 Cast Media Playback** - Phases 6-8 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>✅ v1.0 MVP (Phases 1-5) - SHIPPED 2026-01-15</summary>

### Phase 1: Foundation
**Goal**: Project scaffolding and Docker configuration
**Status**: Complete

### Phase 2: Browser Automation
**Goal**: Playwright with authentication injection
**Status**: Complete

### Phase 3: Video Encoding Pipeline
**Goal**: FFmpeg with Xvfb capture
**Status**: Complete

### Phase 4: Cast Protocol Integration
**Goal**: pychromecast device discovery and connection
**Status**: Complete

### Phase 5: Webhook API System
**Goal**: FastAPI endpoints for start/stop/status
**Status**: Complete

</details>

### 🚧 v1.1 Cast Media Playback (In Progress)

**Milestone Goal:** Complete the Cast playback pipeline with dual-mode streaming for both dashboard reliability and camera feed low-latency.

- [x] **Phase 6: HTTP Streaming Server** - Serve video streams to Cast device
- [ ] **Phase 7: FFmpeg Dual-Mode Output** - Configure encoder for HLS and fMP4 modes
- [ ] **Phase 8: Cast Media Playback** - Wire media_controller to display stream on TV

## Phase Details

### Phase 6: HTTP Streaming Server
**Goal**: HTTP endpoints serve HLS and fMP4 video streams that Cast device can access
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: STRM-01, STRM-02, STRM-04, STRM-05, STRM-06, NET-01, NET-02
**Success Criteria** (what must be TRUE):
  1. HTTP endpoint serves video stream accessible from Cast device's network
  2. HLS mode generates playlist with `application/vnd.apple.mpegurl` content type
  3. fMP4 mode generates fragmented MP4 stream with `video/mp4` content type
  4. CORS headers allow Cast device access
  5. Host IP auto-detected for stream URL construction
**Research**: Unlikely (FastAPI HTTP serving is established pattern)
**Plans**: TBD

### Phase 7: FFmpeg Dual-Mode Output
**Goal**: FFmpeg pipeline produces both HLS segments and fMP4 streams based on mode parameter
**Depends on**: Phase 6
**Requirements**: ENC-01, ENC-02, ENC-03, ENC-04, STRM-03
**Success Criteria** (what must be TRUE):
  1. HLS output generates MPEG-TS segments with playlist file
  2. fMP4 output generates fragmented MP4 for low-latency streaming
  3. H.264 High Profile Level 4.1 used for universal Cast compatibility
  4. AAC audio encoding works for Cast playback
  5. Mode selection via webhook parameter switches between outputs
**Research**: Unlikely (FFmpeg configuration from v1.0 research)
**Plans**: TBD

### Phase 8: Cast Media Playback
**Goal**: Cast device plays HTTP video stream from our server
**Depends on**: Phase 7
**Requirements**: CAST-01, CAST-02, CAST-03
**Success Criteria** (what must be TRUE):
  1. `media_controller.play_media()` successfully starts playback on Cast device
  2. HLS streams use BUFFERED stream_type
  3. fMP4 streams use LIVE stream_type
  4. Correct content_type passed based on mode
**Research**: Unlikely (pychromecast media_controller already used in v1.0)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 6 → 7 → 8

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 6. HTTP Streaming Server | v1.1 | 2/2 | Complete | 2026-01-17 |
| 7. FFmpeg Dual-Mode Output | v1.1 | 1/2 | In progress | - |
| 8. Cast Media Playback | v1.1 | 0/TBD | Not started | - |
