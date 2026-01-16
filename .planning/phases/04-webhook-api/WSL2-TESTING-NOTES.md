# WSL2 Testing Notes - Phase 4

**Date**: 2026-01-16
**Environment**: WSL2 (Linux 6.6.87.2-microsoft-standard-WSL2) + Docker

## Issue: Cast Device Discovery Fails in WSL2

### Symptoms
- Cast device visible and functional in Windows Chrome browser
- Device NOT discovered when running service in WSL2 (native Python or Docker)
- mDNS discovery returns empty list even with Docker `--network host`

### Root Cause
WSL2 uses a virtualized NAT network that doesn't properly forward mDNS/multicast packets between Windows host and Linux guest. Even with Docker host networking, the multicast packets required for Cast device discovery (mDNS/DNS-SD) don't reach the service.

### User's Cast Device
- **IP Address**: 10.10.0.31
- **Status**: Discoverable from Windows, not from WSL2/Docker
- **Network**: Same local network as development machine

### Testing Results

**What Works** ✓:
- Service starts successfully: `python -m src.main`
- All HTTP endpoints respond correctly
- Structured JSON logging functional
- Non-blocking webhook pattern verified
- Background task creation successful
- Error handling and cleanup working

**What Doesn't Work** ⚠️:
- mDNS Cast device discovery (environmental limitation)
- End-to-end casting verification in WSL2

### Workarounds Attempted

1. **Native WSL2 Python** - Failed (no mDNS)
2. **Docker with host networking** - Failed (mDNS still blocked by WSL2)
3. **Direct IP connection** - Blocked by pychromecast requiring mDNS metadata

### Solution for Phase 5

Add environment variable configuration for static IP:

```bash
CAST_DEVICE_IP=10.10.0.31
CAST_DEVICE_NAME="Living Room TV"  # Optional override
```

Update Cast discovery code to:
1. Try mDNS discovery first
2. If fails and `CAST_DEVICE_IP` set, connect directly by IP
3. Skip discovery metadata requirement for IP-based connections

### Testing Recommendations

For full end-to-end testing with physical Cast devices:

1. **Native Linux** - mDNS works properly
2. **Native macOS** - mDNS works properly
3. **Native Windows Python** - mDNS works properly
4. **Docker on Linux/macOS** - Works with host networking
5. **WSL2** - Use static IP configuration (Phase 5 feature)

### Documentation Updates

- Added end-to-end testing section to VERIFICATION.md
- Documented WSL2 limitation in STATE.md blockers
- Noted Phase 5 requirement for IP-based configuration
- Clarified that webhook API is fully functional (limitation is Cast discovery only)

### Conclusion

**Phase 4 Status**: ✓ COMPLETE

The webhook API is fully functional and all success criteria met. Cast device discovery failure in WSL2 is an environmental limitation, not a code defect. The Cast integration code is correct (verified in Phase 2). Adding IP-based configuration in Phase 5 will enable testing in WSL2 environments.
