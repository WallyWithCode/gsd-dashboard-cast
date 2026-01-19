# Proxmox Intel QuickSync GPU Passthrough Guide

## Overview

This guide enables Intel QuickSync hardware acceleration for the Dashboard Cast Service running in Proxmox VMs or LXC containers. QuickSync reduces CPU usage by 80-90% per stream by offloading H.264 encoding to the Intel integrated GPU.

**Requirements:**
- Proxmox VE 7.0+ (tested on 8.2.7)
- Intel CPU with integrated graphics (NOT "F" suffix models like i9-14900KF)
- Intel Gen 8+ CPU recommended (Broadwell 2014+) for iHD driver support

## Deployment Options

### Option 1: LXC Container (Recommended)

Simpler setup, better performance, privileged container required for device access.

### Option 2: VM with GPU Passthrough

More complex setup, requires IOMMU/VT-d, use if LXC not suitable.

---

## LXC Container Setup (Recommended)

### Step 1: Enable IOMMU in Proxmox Host

Even LXC containers require IOMMU enabled for GPU device access.

1. Check CPU support:
```bash
dmesg | grep -e DMAR -e IOMMU
# Should show: "DMAR: IOMMU enabled" or similar
```

2. Edit GRUB configuration on Proxmox host:
```bash
nano /etc/default/grub
```

3. Add IOMMU parameters to GRUB_CMDLINE_LINUX_DEFAULT:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"
```

4. Update GRUB and reboot:
```bash
update-grub
reboot
```

5. Verify after reboot:
```bash
dmesg | grep -e DMAR -e IOMMU
# Should show "IOMMU enabled"
```

### Step 2: Identify GPU Device

On Proxmox host, identify Intel GPU device:

```bash
ls -l /dev/dri/
# Look for: renderD128 (render node for encoding)
# May also see: card0 (display output)
```

Note the major:minor device numbers (usually 226:128 for renderD128).

### Step 3: Configure LXC Container

1. Edit container config on Proxmox host:
```bash
nano /etc/pve/lxc/<CTID>.conf
```

2. Add device passthrough lines:
```
lxc.cgroup2.devices.allow: c 226:0 rwm
lxc.cgroup2.devices.allow: c 226:128 rwm
lxc.mount.entry: /dev/dri/card0 dev/dri/card0 none bind,optional,create=file
lxc.mount.entry: /dev/dri/renderD128 dev/dri/renderD128 none bind,optional,create=file
```

3. Restart container:
```bash
pct stop <CTID>
pct start <CTID>
```

### Step 4: Configure Groups Inside Container

Enter container and set up permissions:

```bash
pct enter <CTID>

# Check if /dev/dri exists
ls -l /dev/dri

# Get render and video group IDs using helper script
cd /path/to/dashboard-cast
scripts/detect-gpu-gids.sh

# Update docker-compose.yml with actual GIDs:
# Replace RENDER_GID with the number from render group
# Replace VIDEO_GID with the number from video group
```

**Note:** The `scripts/detect-gpu-gids.sh` helper script was created in Plan 10-01 Task 2. It automates detection of render and video group IDs, which vary by distribution. Run this script to get the correct GID values for your system.

### Step 5: Install Drivers in Container

Inside container (or rebuild Docker image):

```bash
apt-get update
apt-get install -y \
    intel-media-va-driver-non-free \
    vainfo \
    libva2 \
    libva-drm2
```

### Step 6: Verify Hardware Access

Inside container:

```bash
# Check VAAPI driver loads
vainfo --display drm --device /dev/dri/renderD128

# Expected output includes:
# - Driver version: Intel iHD driver
# - VAProfileH264High : VAEntrypointEncSlice

# Check FFmpeg recognizes encoder
ffmpeg -encoders | grep h264_qsv

# Expected: h264_qsv (H.264 / AVC ... Intel Quick Sync Video acceleration)
```

---

## VM Setup (Alternative)

### Step 1-2: Enable IOMMU (Same as LXC)

Follow LXC Step 1 for IOMMU enablement.

### Step 3: Identify IOMMU Group

```bash
# On Proxmox host
find /sys/kernel/iommu_groups/ -type l | grep -i vga
# Note the IOMMU group number
```

### Step 4: Configure VM for PCI Passthrough

1. In Proxmox web UI: VM > Hardware > Add > PCI Device
2. Select Intel VGA device
3. Enable: All Functions, Primary GPU (if applicable)
4. Restart VM

### Step 5: Install Drivers in VM (Same as LXC Step 5-6)

Follow LXC steps 5-6 inside the VM.

---

## Troubleshooting

### /dev/dri does not exist

**Cause:** IOMMU not enabled, or device not passed through.

**Fix:**
- Verify IOMMU enabled: `dmesg | grep IOMMU`
- Check LXC config has lxc.mount.entry lines
- Restart container: `pct stop <CTID> && pct start <CTID>`

### Permission denied on /dev/dri/renderD128

**Cause:** Container user not in render/video groups.

**Fix:**
- Inside container: `ls -l /dev/dri/renderD128` (check group ownership)
- Run scripts/detect-gpu-gids.sh to get correct GIDs
- Update docker-compose.yml group_add with correct GIDs
- Rebuild container: `docker-compose down && docker-compose up -d`

### vainfo shows i965 driver instead of iHD

**Cause:** Wrong driver selected (i965 is legacy, archived 2025).

**Fix:**
- Set environment variable in docker-compose.yml: `LIBVA_DRIVER_NAME=iHD`
- Verify: `vainfo | grep "Driver version"` should show "iHD"

### h264_qsv not found in ffmpeg -encoders

**Cause:** FFmpeg package doesn't include QSV support, or drivers missing.

**Fix:**
- Ensure intel-media-va-driver-non-free installed
- Check Debian/Ubuntu FFmpeg package includes --enable-vaapi
- Verify: `ffmpeg -hwaccels` should list "qsv"

### CPU has "F" suffix (e.g., i9-14900KF)

**Cause:** "F" models lack integrated graphics.

**Fix:** QuickSync requires integrated GPU. Use non-F model CPU (e.g., i9-14900K).

---

## Verification Checklist

After setup, verify all components:

- [ ] IOMMU enabled: `dmesg | grep IOMMU` shows "enabled"
- [ ] /dev/dri exists in container: `ls -l /dev/dri`
- [ ] vainfo succeeds: `vainfo --display drm --device /dev/dri/renderD128`
- [ ] vainfo shows iHD driver (not i965)
- [ ] vainfo shows VAEntrypointEncSlice for H264High profile
- [ ] h264_qsv in ffmpeg: `ffmpeg -encoders | grep h264_qsv`
- [ ] scripts/detect-gpu-gids.sh available and executable
- [ ] Health endpoint reports QuickSync: `curl http://localhost:8000/health | jq .hardware_acceleration`

---

## References

- [Proxmox PCI Passthrough Wiki](https://pve.proxmox.com/wiki/PCI_Passthrough)
- [FFmpeg Hardware/QuickSync Wiki](https://trac.ffmpeg.org/wiki/Hardware/QuickSync)
- [Jellyfin Intel GPU HWA Guide](https://jellyfin.org/docs/general/administration/hardware-acceleration/intel/)
- Project research: `.planning/phases/10-intel-quicksync-hardware-acceleration/10-RESEARCH.md`

---

*Guide created: 2026-01-19*
*Tested on: Proxmox VE 8.2.7 with Intel CPUs Gen 8+*
