---
created: 2026-01-19T13:25
title: Fix webpage centering and scaling issues
area: video
files:
  - src/browser/manager.py
  - src/video/config.py
---

## Problem

When streaming, webpages that should display centered content are showing items misaligned (bottom-right of screen instead of centered). This suggests the browser viewport or x11grab capture dimensions are misconfigured, causing content to render at wrong resolution or aspect ratio.

User reported: "the window appears that it is scaled to a resolution that means that the items on the webpage that should be centred, are on the bottom right of the screen"

Possible causes:
1. Xvfb display resolution doesn't match FFmpeg capture resolution
2. Browser viewport size doesn't match capture dimensions
3. Quality presets (720p, 1080p) have wrong resolution mapping
4. CSS media queries responding to incorrect viewport size

## Solution

1. Verify Xvfb display resolution matches quality preset resolution
2. Ensure Playwright viewport matches x11grab capture size exactly
3. Add verification step to confirm browser reports correct window.innerWidth/innerHeight
4. Test with known-centered webpage (e.g., Google homepage) to validate alignment
5. Check if DPI scaling or fractional scaling is causing offset

Files to investigate:
- src/browser/manager.py (viewport configuration)
- src/video/config.py (QualityPreset resolution definitions)
- src/display/xvfb.py (Xvfb display size configuration)
