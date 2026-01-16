---
created: 2026-01-16T12:15
title: Implement Cast media playback
area: video
files:
  - src/cast/session.py:120-152
  - src/video/stream.py:145-148
---

## Problem

The v1.0 streaming pipeline runs (Xvfb, Browser, FFmpeg all working) and the Cast session connects successfully (HDMI-CEC wakes TV), but actual media playback to the Cast device is not implemented.

The `start_cast()` method in `session.py:120` is a placeholder that logs the request but doesn't call `media_controller.play_media()`. The stream.py code creates the Cast session context but never invokes media playback.

To display video on TV, we need:
1. HTTP server to serve HLS playlist (Cast needs network-accessible URL)
2. Get Docker host IP so Cast device can reach the server
3. Call `media_controller.play_media()` with the stream URL
4. Handle Cast's supported media types (may need different format than HLS)

Discovered during v1.0 testing when everything ran but nothing appeared on TV.

## Solution

1. Add aiohttp-based HTTP server to serve `/tmp/streams/` directory
2. Detect host IP accessible from Cast device network
3. Wire up `session.start_cast(http://{host_ip}:{port}/{stream}.m3u8)`
4. Research Cast HLS support vs alternative formats (MP4 fragment?)

Could be v1.1 scope or critical v1.0 fix depending on priority.
