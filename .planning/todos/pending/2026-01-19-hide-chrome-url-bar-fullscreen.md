---
created: 2026-01-19T13:25
title: Hide Chrome URL bar and enable fullscreen mode
area: video
files:
  - src/browser/manager.py
---

## Problem

During streaming, the Chrome headless window shows the URL bar at the top, which wastes screen space and appears unprofessional on the Cast device display. The URL bar serves no purpose since this is automated browser capture for streaming.

User reported: "when streaming, the chrome window has the url bar visible, this takes up screen space and isnt needed, can we run in fullscreen mode?"

## Solution

Configure Playwright/Chromium to launch in fullscreen or kiosk mode:
- Add `--kiosk` flag to Chrome launch options
- Or use `--start-fullscreen` flag
- Or programmatically call fullscreen API after page load
- Verify that fullscreen mode doesn't interfere with x11grab capture dimensions

Files to modify:
- src/browser/manager.py (Playwright launch configuration)
