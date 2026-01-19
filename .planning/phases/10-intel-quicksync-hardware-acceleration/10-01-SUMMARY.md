---
phase: 10-intel-quicksync-hardware-acceleration
plan: 01
subsystem: infra
tags: [docker, ffmpeg, intel-quicksync, vaapi, hardware-acceleration, h264-qsv]

# Dependency graph
requires:
  - phase: 09-hls-buffering-fix
    provides: HLS streaming infrastructure and FFmpeg subprocess management
provides:
  - Docker infrastructure configured for Intel QuickSync hardware acceleration
  - FFmpeg 7.1+ with h264_qsv encoder support
  - VAAPI drivers (iHD) installed in container
  - GPU device passthrough configuration in docker-compose.yml
  - Helper script to detect host GPU group IDs
affects: [11-fmp4-validation, 12-stop-detection, 13-process-lifecycle, hardware-encoding]

# Tech tracking
tech-stack:
  added: [intel-media-va-driver, vainfo, libva2, libva-drm2]
  patterns: [GPU device passthrough, VAAPI driver configuration, group permission management]

key-files:
  created:
    - scripts/detect-gpu-gids.sh
  modified:
    - Dockerfile
    - docker-compose.yml

key-decisions:
  - "FFmpeg 7.1.3 available in python:3.11-slim base image - no need for Debian testing repository"
  - "intel-media-va-driver package name (not intel-media-va-driver-non-free) in Debian Trixie"
  - "LIBVA_DRIVER_NAME=iHD environment variable to force iHD driver selection"
  - "Placeholder GID values in docker-compose.yml with helper script for detection"

patterns-established:
  - "GPU passthrough: /dev/dri device mapping + render/video group permissions"
  - "FFmpeg version verification: Build-time check for 7.0+ requirement"
  - "Host-specific configuration: Helper scripts for environment-dependent values"

# Metrics
duration: 7min
completed: 2026-01-19
---

# Phase 10 Plan 01: Docker Infrastructure for Intel QuickSync Summary

**Docker infrastructure configured with FFmpeg 7.1.3, Intel iHD VAAPI drivers, and GPU device passthrough for h264_qsv hardware encoding**

## Performance

- **Duration:** 7 min 28 sec
- **Started:** 2026-01-19T10:46:43Z
- **Completed:** 2026-01-19T10:54:11Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Installed Intel media VAAPI drivers (iHD) and verification tools in Docker container
- Added FFmpeg 7.0+ version verification with h264_qsv encoder check at build time
- Configured /dev/dri GPU device passthrough in docker-compose.yml
- Created helper script to detect host render and video group IDs for GPU access
- Set LIBVA_DRIVER_NAME=iHD to force correct driver selection

## Task Commits

Each task was committed atomically:

1. **Task 1: Update Dockerfile with Intel media drivers** - `5e24248` (feat)
2. **Task 2: Update docker-compose.yml with GPU passthrough** - `6f65118` (feat)

## Files Created/Modified
- `Dockerfile` - Added intel-media-va-driver, vainfo, libva2, libva-drm2 packages; FFmpeg 7.0+ verification with h264_qsv encoder check
- `docker-compose.yml` - Added /dev/dri device passthrough, group_add for render/video groups, LIBVA_DRIVER_NAME environment variable
- `scripts/detect-gpu-gids.sh` - Helper script to detect host render and video group IDs for docker-compose.yml configuration

## Decisions Made

**1. Simplified FFmpeg installation approach**
- **Context:** Plan specified installing FFmpeg 7.0+ from Debian testing repository with apt pinning
- **Discovery:** python:3.11-slim base image already includes FFmpeg 7.1.3-0+deb13u1 with h264_qsv support
- **Decision:** Use existing FFmpeg from base image instead of complex repository mixing
- **Rationale:** Avoids dependency conflicts between Debian stable and testing; simpler, more maintainable
- **Impact:** Faster builds, no repository priority management needed

**2. Corrected Intel media driver package name**
- **Context:** Plan specified intel-media-va-driver-non-free package
- **Discovery:** Package not available in Debian Trixie (repository for python:3.11-slim)
- **Resolution:** Correct package name is intel-media-va-driver (without -non-free suffix)
- **Verification:** Package installs successfully, provides iHD VAAPI driver for Gen 8+ GPUs

**3. Placeholder GID values with helper script**
- **Context:** Group IDs vary by distribution and system configuration
- **Decision:** Use placeholder "RENDER_GID" and "VIDEO_GID" strings in docker-compose.yml
- **Implementation:** Created scripts/detect-gpu-gids.sh to detect actual host values
- **Rationale:** Makes configuration portable and self-documenting; user runs script to get correct values
- **User action required:** Run detect-gpu-gids.sh and replace placeholders before deployment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed FFmpeg installation approach**
- **Found during:** Task 1 (Dockerfile modifications)
- **Issue:** Plan's Debian testing repository approach caused dependency conflicts (mesa libgallium version mismatches between stable and testing)
- **Discovery:** Base image already has FFmpeg 7.1.3 with h264_qsv support - complex repository mixing unnecessary
- **Fix:** Simplified to use existing FFmpeg from base image, added Intel media drivers to existing apt-get install line
- **Files modified:** Dockerfile (simplified from 3-stage repository setup to single apt-get install)
- **Verification:** Docker build succeeds, FFmpeg 7.1.3 confirmed, h264_qsv encoder present
- **Committed in:** 5e24248 (Task 1 commit)

**2. [Rule 3 - Blocking] Corrected Intel media driver package name**
- **Found during:** Task 1 (Dockerfile build failure)
- **Issue:** intel-media-va-driver-non-free package does not exist in Debian Trixie
- **Fix:** Changed to intel-media-va-driver (correct package name for current Debian release)
- **Files modified:** Dockerfile
- **Verification:** Package installs successfully, vainfo available in container
- **Committed in:** 5e24248 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking issues)
**Impact on plan:** Both auto-fixes were necessary to complete task execution. Simplified approach is more maintainable than plan's complex repository mixing. No scope creep - same functionality achieved with cleaner implementation.

## Issues Encountered

**Dependency conflict with Debian testing repository**
- **Problem:** Initial plan approach mixed Debian stable (Bookworm) and testing (Trixie) repositories, causing mesa/libva version conflicts that prevented xvfb installation
- **Root cause:** FFmpeg 7.0 from testing requires newer libva2, but xvfb from stable depends on mesa packages incompatible with testing versions
- **Resolution:** Discovered base image already provides FFmpeg 7.1.3 - no repository mixing needed
- **Lesson:** Always check base image package versions before adding external repositories

## User Setup Required

**Before deploying with hardware acceleration:**

1. Run GPU group detection script:
   ```bash
   ./scripts/detect-gpu-gids.sh
   ```

2. Update docker-compose.yml group_add section with actual GIDs:
   ```yaml
   group_add:
     - "992"   # Replace RENDER_GID with output from script
     - "44"    # Replace VIDEO_GID with output from script
   ```

3. Verify /dev/dri device exists on host:
   ```bash
   ls -la /dev/dri/
   ```
   Should show renderD128 (GPU device) - if missing, Intel GPU may not be available or IOMMU/SR-IOV not configured

4. Verify host has Intel GPU with QuickSync support:
   ```bash
   lspci | grep -i vga
   ```
   Should show Intel graphics device (Gen 8+ required for h264_qsv)

**No external service configuration required.** All changes are Docker infrastructure only.

## Next Phase Readiness

**Ready for Phase 10 Plan 02 (FFmpeg Integration):**
- Docker infrastructure supports GPU passthrough
- FFmpeg 7.1.3 with h264_qsv encoder verified available
- VAAPI drivers installed and configured
- Device permissions framework established (pending GID configuration)

**Blockers:**
- None - infrastructure ready for FFmpeg encoder parameter integration

**Considerations for next phase:**
- Hardware acceleration requires /dev/dri device on host (Proxmox GPU passthrough)
- Phase 10-02 will add h264_qsv encoder parameters to FFmpeg command
- Phase 10-03 will test with actual GPU and verify encoding performance
- Current setup allows graceful degradation: h264_qsv encoder available but won't work without /dev/dri until host GPU passthrough configured

**Testing dependencies:**
- Host system needs Intel GPU with IOMMU/SR-IOV passthrough configured
- VM/container needs /dev/dri device access
- Plan 10-03 will handle verification and fallback scenarios

---
*Phase: 10-intel-quicksync-hardware-acceleration*
*Completed: 2026-01-19*
