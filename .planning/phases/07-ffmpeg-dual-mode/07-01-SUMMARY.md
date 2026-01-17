---
phase: 07-ffmpeg-dual-mode
plan: 01
subsystem: video
tags: [ffmpeg, hls, fmp4, h264, aac, chromecast]

# Dependency graph
requires:
  - phase: 06-http-streaming-server
    provides: HTTP endpoints for serving video streams
provides:
  - Dual-mode FFmpeg encoding (HLS and fMP4)
  - H.264 High Profile Level 4.1 for Cast compatibility
  - AAC audio encoding with silent source
affects: [08-cast-media-playback]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual-mode output via mode parameter"
    - "Silent audio source using lavfi anullsrc"
    - "Fragmented MP4 with streaming movflags"

key-files:
  created: []
  modified:
    - src/video/encoder.py

key-decisions:
  - "Use H.264 High Profile Level 4.1 for universal Cast compatibility"
  - "Add silent audio track via anullsrc filter (Cast devices expect audio)"
  - "fMP4 uses frag_keyframe+empty_moov+default_base_moof flags for streaming"

# Metrics
duration: 3 min
completed: 2026-01-17
---

# Phase 7 Plan 1: FFmpeg Dual-Mode Output Summary

**FFmpegEncoder now supports mode='hls' for buffered dashboard streaming and mode='fmp4' for low-latency camera feeds, with H.264 High 4.1 + AAC audio for Cast compatibility.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-17T17:55:24Z
- **Completed:** 2026-01-17T17:58:37Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added `mode` parameter to FFmpegEncoder: 'hls' (buffered) or 'fmp4' (low-latency)
- HLS mode produces .m3u8 playlist with .ts segments (2-second segments, keep 3)
- fMP4 mode produces fragmented MP4 with streaming-friendly movflags
- Added H.264 High Profile Level 4.1 for universal Chromecast compatibility
- Added silent audio track generation using lavfi anullsrc filter
- Added AAC audio encoding at 128kbps for Cast playback compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Add mode parameter and dual-mode FFmpeg output** - `6fdc64b` (feat)
2. **Task 2: Add AAC audio encoding for Cast playback** - `1968784` (feat)

## Files Created/Modified

- `src/video/encoder.py` - Added mode parameter, dual-mode output logic, H.264 profile/level, AAC audio encoding

## Decisions Made

1. **H.264 High Profile Level 4.1** - Universal Cast compatibility (all Chromecast generations support this)
2. **Silent audio via anullsrc** - Cast devices expect audio tracks; generates 44.1kHz stereo silence
3. **fMP4 movflags** - `frag_keyframe+empty_moov+default_base_moof` enables:
   - Fragmentation at keyframes for seekability
   - Empty moov for streaming before file complete
   - Default base moof for Cast compatibility
4. **-shortest flag** - Ensures encoding stops when video ends, not waiting for infinite audio

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FFmpegEncoder ready for mode selection from webhook endpoint
- Phase 7 Plan 2 will add mode selection to webhook API
- Phase 8 will wire media_controller.play_media() with correct content types

---
*Phase: 07-ffmpeg-dual-mode*
*Completed: 2026-01-17*
