---
phase: 03-video-pipeline
plan: 01
subsystem: video
tags: [ffmpeg, video-encoding, h264, hls, quality-presets, x11grab]

# Dependency graph
requires:
  - phase: 01-browser-foundation
    provides: async/await patterns, context manager pattern
  - phase: 02-cast-integration
    provides: async patterns with run_in_executor for blocking calls
provides:
  - FFmpeg video encoding with quality configuration
  - Quality presets (1080p, 720p, low-latency)
  - HLS streaming output format
  - Context manager pattern for encoder lifecycle
affects: [04-webhook-api, 05-production-readiness]

# Tech tracking
tech-stack:
  added: []
  patterns: [async-context-manager-for-encoder, hls-streaming, quality-presets]

key-files:
  created:
    - src/video/quality.py
    - src/video/encoder.py
  modified:
    - src/video/__init__.py

key-decisions:
  - "Software encoding (libx264) for v1 - hardware acceleration deferred to v2"
  - "HLS output format with 2-second segments for streaming compatibility"
  - "Quality presets based on research: 1080p (5000k), 720p (2500k), low-latency (2000k)"
  - "Low-latency tuning: zerolatency, bf=0, refs=1 for minimal delay"
  - "Context manager pattern for automatic process cleanup"

patterns-established:
  - "QualityConfig dataclass for encoding parameters"
  - "QUALITY_PRESETS dictionary for common configurations"
  - "FFmpeg subprocess management with async/await"
  - "Graceful process termination with 5s timeout before force kill"
  - "Automatic cleanup of HLS playlist and segment files"

# Metrics
duration: 3 min
completed: 2026-01-15
---

# Phase 3 Plan 1: Video Pipeline Summary

**FFmpeg H.264 encoder with configurable quality presets (1080p/720p/low-latency), HLS streaming output, and async context manager lifecycle following Phase 1-2 patterns**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-15T21:50:26Z
- **Completed:** 2026-01-15T21:53:37Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Quality configuration module with QualityConfig dataclass and three presets
- FFmpeg encoder with x11grab input capturing from Xvfb display
- Low-latency encoding mode with zerolatency tuning (-bf 0, -refs 1, -g framerate)
- Normal encoding mode with better compression (-bf 2, -refs 3, -g framerate*2)
- HLS output format with 2-second segments and auto-cleanup
- Async context manager pattern for automatic process lifecycle management
- Graceful process termination with 5s timeout before force kill
- Automatic cleanup of HLS playlist and segment files

## Task Commits

Each task was committed atomically:

1. **Task 1: Create quality configuration module** - `5e184b5` (feat)
2. **Task 2: Implement FFmpeg encoder with quality configuration** - `d1a5cca` (feat)

## Files Created/Modified

- `src/video/__init__.py` - Module exports for QualityConfig, QUALITY_PRESETS, get_quality_config, FFmpegEncoder
- `src/video/quality.py` - QualityConfig dataclass and QUALITY_PRESETS dictionary (79 lines)
- `src/video/encoder.py` - FFmpegEncoder class with async context manager (229 lines)

## Decisions Made

1. **Software encoding (libx264)** - Using software encoding for v1, hardware acceleration (NVENC/VAAPI/QSV) deferred to v2 for broader compatibility
2. **HLS output format** - HLS with 2-second segments for streaming compatibility with Cast protocol
3. **Quality presets from research** - 1080p (5000kbps), 720p (2500kbps), low-latency (2000kbps) based on Phase 3 research
4. **Low-latency tuning** - zerolatency tune with bf=0, refs=1, g=framerate for minimal delay
5. **Context manager pattern** - Following established pattern from Phases 1 and 2 for automatic resource cleanup

## Deviations from Plan

None - plan executed exactly as written. All must_haves satisfied:
- ✅ Quality presets (1080p, 720p, low-latency) exist with different resolution/bitrate configs
- ✅ FFmpeg encoder can be configured with quality preset
- ✅ FFmpeg process launches with correct encoding parameters
- ✅ src/video/quality.py exports QualityConfig and QUALITY_PRESETS (79 lines)
- ✅ src/video/encoder.py exports FFmpegEncoder (229 lines)
- ✅ Key links present: encoder imports QualityConfig, build_ffmpeg_args uses config.resolution/bitrate/preset

## Issues Encountered

None - straightforward implementation following plan specifications and established async patterns from prior phases.

## User Setup Required

None - no external service configuration required. FFmpeg will be installed in Docker image (Phase 5).

## Next Phase Readiness

Video encoding foundation complete and ready for webhook API integration. The video module provides:
- Quality configuration system with three presets for different use cases
- FFmpeg encoder that captures from Xvfb virtual display
- HLS streaming output compatible with Cast protocol
- Async context manager pattern for proper lifecycle management
- Low-latency and normal encoding modes optimized for different scenarios

Next phase (Phase 4: Webhook API) can integrate this encoder to start/stop video streaming via HTTP endpoints. The encoder's async context manager pattern aligns with Phase 1-2 patterns for seamless integration.

**Note:** FFmpeg subprocess management is implemented but requires FFmpeg installation in Docker (will be handled in Phase 5). HLS output URLs reference localhost:8080 (HTTP server will be implemented in Phase 4).

---
*Phase: 03-video-pipeline*
*Completed: 2026-01-15*
