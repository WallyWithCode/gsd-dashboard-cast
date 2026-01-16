---
created: 2026-01-16T12:32
title: Direct RTSP to Cast streaming
area: video
files: []
---

## Problem

Current architecture captures camera feeds via browser (Playwright renders dashboard with camera widget, FFmpeg captures the screen). This adds latency from:
1. Browser rendering the video element
2. Screen capture overhead
3. Re-encoding the already-decoded video

For camera feeds where latency is critical, bypassing the browser entirely would provide the lowest possible latency path to Chromecast.

## Solution

Add alternative pipeline for RTSP sources:
1. Accept RTSP URL directly in webhook (instead of dashboard URL)
2. FFmpeg transcodes RTSP → Cast-compatible format (fMP4)
3. Stream directly to Cast device

This would be a separate code path from dashboard casting, optimized for:
- Security cameras
- Live video feeds
- Any RTSP/RTMP source

TBD: Authentication handling for secured RTSP streams.
