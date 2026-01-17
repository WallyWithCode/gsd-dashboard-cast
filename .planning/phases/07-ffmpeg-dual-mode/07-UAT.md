---
status: testing
phase: 07-ffmpeg-dual-mode
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md]
started: 2026-01-17T18:15:00Z
updated: 2026-01-17T18:15:00Z
---

## Current Test

number: 1
name: HLS Mode Output Files
expected: |
  With mode='hls' (or no mode specified), FFmpegEncoder produces:
  - A .m3u8 playlist file
  - .ts segment files in the stream directory
  Verify by checking /tmp/streams/ after starting a stream.
awaiting: user response

## Tests

### 1. HLS Mode Output Files
expected: With mode='hls' (or no mode specified), FFmpegEncoder produces .m3u8 playlist and .ts segment files
result: [pending]

### 2. fMP4 Mode Output Files
expected: With mode='fmp4', FFmpegEncoder produces a single .mp4 file (not playlist+segments)
result: [pending]

### 3. Webhook Mode Parameter
expected: POST to /start with {"url": "...", "mode": "fmp4"} accepts the mode parameter without error
result: [pending]

### 4. Default Mode is HLS
expected: POST to /start without mode parameter defaults to HLS output (produces .m3u8)
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0

## Issues for /gsd:plan-fix

[none yet]
