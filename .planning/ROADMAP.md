# Roadmap: Dashboard Cast Service

## Overview

Transform web dashboards into Cast-enabled video streams through five focused phases: establish browser automation foundation with proper resource management, integrate Cast protocol for device connectivity, build FFmpeg video pipeline with quality controls, expose webhook API for automation triggers, and package for production deployment. Each phase delivers independently verifiable capability building toward webhook-triggered dashboard casting for Home Assistant automations.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Browser Foundation** - Playwright automation with authentication and resource management
- [x] **Phase 2: Cast Integration** - Cast protocol connectivity with device discovery
- [x] **Phase 3: Video Pipeline** - FFmpeg encoding with quality configuration
- [ ] **Phase 4: Webhook API** - FastAPI endpoints with async processing
- [ ] **Phase 5: Production Readiness** - Docker packaging and documentation

## Phase Details

### Phase 1: Browser Foundation
**Goal**: Playwright browser automation with authentication and resource management
**Depends on**: Nothing (first phase)
**Requirements**: BROWSER-01, BROWSER-02, INFRA-01
**Success Criteria** (what must be TRUE):
  1. Browser instance launches and renders web pages
  2. Authentication cookies/tokens inject before page load
  3. Browser cleanup occurs without resource leaks
  4. Docker container runs with proper shared memory configuration
**Research**: Unlikely (Playwright patterns well-documented, official docs comprehensive)
**Plans**: Complete

Plans:
- [x] 01-01: Playwright browser automation with auth injection and cleanup
- [x] 01-02: Docker packaging with shared memory and host networking

### Phase 2: Cast Integration
**Goal**: Cast protocol connectivity with device discovery and playback control
**Depends on**: Phase 1
**Requirements**: CAST-01, CAST-02, CAST-03, CAST-04, CAST-05
**Success Criteria** (what must be TRUE):
  1. Service discovers Cast devices on local network
  2. Service initiates and maintains Cast session
  3. Service stops casting on command
  4. TV wakes via HDMI-CEC when casting starts
  5. Failed connections retry with exponential backoff
**Research**: Unlikely (pychromecast examples cover 90% of use cases, Home Assistant integration guide extensive)
**Plans**: Complete

Plans:
- [x] 02-01: Cast device discovery and session management with HDMI-CEC wake
- [x] 02-02: Retry mechanism with exponential backoff and comprehensive testing

### Phase 3: Video Pipeline
**Goal**: FFmpeg encoding with quality configuration for streaming
**Depends on**: Phase 2
**Requirements**: BROWSER-04, WEBHOOK-05
**Success Criteria** (what must be TRUE):
  1. Web page renders to video stream with configurable quality
  2. Video quality presets work (1080p, 720p, low-latency)
  3. Cast session auto-stops after configured duration
  4. End-to-end latency stays under 5 seconds
**Research**: Likely (hardware acceleration varies by deployment target)
**Research topics**: FFmpeg hardware acceleration options (NVENC/VAAPI/QSV), target environment GPU capabilities, low-latency tuning for streaming
**Plans**: Complete

Plans:
- [x] 03-01: FFmpeg encoder with quality configuration and HLS output
- [x] 03-02: Xvfb virtual display management
- [x] 03-03: End-to-end video pipeline integration

### Phase 4: Webhook API
**Goal**: FastAPI webhook endpoints with async processing
**Depends on**: Phase 3
**Requirements**: WEBHOOK-01, WEBHOOK-02, WEBHOOK-03, WEBHOOK-04, INFRA-02
**Success Criteria** (what must be TRUE):
  1. Webhook accepts POST request and starts casting
  2. Webhook accepts POST request and stops casting
  3. Webhook returns immediate status (success/failure)
  4. Service logs all webhook requests and operations
  5. Health check endpoint reports service status
**Research**: Unlikely (FastAPI async patterns standard, webhook handling well-established)
**Plans**: In progress

Plans:
- [x] 04-01: FastAPI foundation with lifespan and structured logging
- [ ] 04-02: Webhook endpoints and stream tracking
- [ ] 04-03: Status and health check endpoints

### Phase 5: Production Readiness
**Goal**: Docker packaging, documentation, and manual testing support
**Depends on**: Phase 4
**Requirements**: BROWSER-03
**Success Criteria** (what must be TRUE):
  1. Service only accepts HTTPS URLs (Cast security requirement)
  2. Documentation covers manual testing with curl/Postman
  3. Docker deployment requires minimal setup
**Research**: Unlikely (Docker packaging established patterns)
**Plans**: TBD

Plans:
- [ ] TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Browser Foundation | 2/2 | Complete | 2026-01-15 |
| 2. Cast Integration | 2/2 | Complete | 2026-01-15 |
| 3. Video Pipeline | 3/3 | Complete | 2026-01-15 |
| 4. Webhook API | 1/3 | In progress | - |
| 5. Production Readiness | 0/TBD | Not started | - |
