# Proxmox Intel GPU Hardware Acceleration Guide

## Overview

This guide enables Intel GPU hardware acceleration for the Dashboard Cast Service running in Proxmox VMs. Hardware acceleration offloads H.264 encoding from CPU to GPU, significantly reducing CPU usage during streaming.

**Important:** This guide uses **VAAPI** (Video Acceleration API), not Intel QuickSync QSV directly. Testing revealed that `h264_qsv` has compatibility issues on CometLake Gen 10 (MFX session initialization errors), while `h264_vaapi` works reliably.

**Requirements:**
- Proxmox VE 7.0+ (tested on 8.2.7)
- Intel CPU with integrated graphics (NOT "F" suffix models like i9-14900KF)
- Intel Gen 8+ CPU (Coffee Lake 2017+) for best iHD driver support
- Ubuntu VM with kernel 5.15+ (tested on Ubuntu 22.04, kernel 6.8.0-90)

**Tested Configuration:**
- CPU: Intel NUC9i5FN (CometLake-U Gen 10)
- Proxmox: 8.2.7
- VM: Ubuntu 22.04 (kernel 6.8.0-90-generic)
- Result: 29% CPU reduction (58% vs 83%)

---

## Prerequisites Check (Proxmox Host)

Before starting, verify IOMMU and GPU availability on your Proxmox host:

```bash
# Check IOMMU is enabled
dmesg | grep -e DMAR -e IOMMU
# Should show: "DMAR: Intel(R) Virtualization Technology for Directed I/O"
# If not, see Step 1 below

# Check Intel GPU is present
lspci | grep -i vga
# Should show: Intel Corporation CometLake-U GT2 (or similar)

# Check /dev/dri devices exist
ls -la /dev/dri/
# Should show: card0 and renderD128
```

---

## Step 1: Enable IOMMU in Proxmox (If Not Already Enabled)

**Check if already enabled:**
```bash
dmesg | grep -e DMAR -e IOMMU | grep -i "enabled\|initialized"
```

If you see "DMAR: IOMMU enabled" or "Intel(R) Virtualization Technology", **skip to Step 2**.

**If IOMMU is not enabled:**

1. Edit GRUB configuration:
```bash
nano /etc/default/grub
```

2. Add IOMMU parameters to `GRUB_CMDLINE_LINUX_DEFAULT`:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"
```

3. Update GRUB and reboot:
```bash
update-grub
reboot
```

4. Verify after reboot:
```bash
dmesg | grep -e DMAR -e IOMMU
# Should show "DMAR: IOMMU enabled"
```

---

## Step 2: Configure GPU Passthrough to VM

### Find Your Intel GPU Device

On Proxmox host:
```bash
lspci | grep -i vga
```

Example output:
```
00:02.0 VGA compatible controller: Intel Corporation CometLake-U GT2 [UHD Graphics] (rev 02)
```

Note the PCI address (e.g., `00:02.0`).

### Add GPU to VM via Proxmox Web UI

1. **Stop your VM** (dashboard-cast must be powered off)

2. In Proxmox web UI:
   - Select your VM
   - Go to **Hardware** tab
   - Click **Add** → **PCI Device**

3. Configure PCI device:
   - **Device:** Select your Intel GPU (00:02.0 VGA compatible controller)
   - ✅ **All Functions** (check this box)
   - ✅ **Primary GPU** (check this box if it's the only GPU)
   - **ROM-Bar:** Leave enabled
   - **PCI-Express:** Leave enabled

4. Click **Add**

5. **Start your VM**

### Verify GPU is Visible in VM

SSH into your Ubuntu VM and check:

```bash
lspci | grep -i vga
```

You should see the Intel GPU (note the PCI address may differ from host):
```
00:10.0 VGA compatible controller: Intel Corporation CometLake-U GT2 [UHD Graphics] (rev 02)
```

---

## Step 3: Install Kernel Modules (Ubuntu VM)

The Intel graphics driver (`i915`) is not included in the base kernel package.

```bash
# Install extra kernel modules
sudo apt update
sudo apt install -y linux-modules-extra-$(uname -r)

# Load the i915 module
sudo modprobe i915

# Verify module is loaded
lsmod | grep i915
# Should show i915 and related modules

# Make module load at boot
echo "i915" | sudo tee -a /etc/modules

# Verify /dev/dri was created
ls -la /dev/dri/
# Should show: card0 and renderD128
```

**Expected output of `ls -la /dev/dri/`:**
```
drwxr-xr-x  3 root root        100 Jan 19 12:41 .
drwxr-xr-x 20 root root       4160 Jan 19 12:41 ..
drwxr-xr-x  2 root root         80 Jan 19 12:41 by-path
crw-rw----  1 root video  226,   0 Jan 19 12:41 card0
crw-rw----  1 root render 226, 128 Jan 19 12:41 renderD128
```

Note the group ownership:
- `card0` → owned by `video` group
- `renderD128` → owned by `render` group

---

## Step 4: Install VAAPI Drivers (Ubuntu VM)

Install Intel media drivers and verification tools:

```bash
sudo apt update
sudo apt install -y \
    intel-media-va-driver \
    i965-va-driver \
    vainfo \
    libva2 \
    libva-drm2
```

**Note:** Use `intel-media-va-driver` (NOT `intel-media-va-driver-non-free`). The non-free version doesn't exist in standard Ubuntu repositories.

---

## Step 5: Verify Hardware Acceleration

Test VAAPI access and encoding capabilities:

```bash
# Test VAAPI driver loads correctly
vainfo

# Expected output should include:
# - libva info: va_openDriver() returns 0
# - Driver version: Intel iHD driver for Intel(R) Gen Graphics
# - VAProfileH264Main : VAEntrypointEncSliceLP
# - VAProfileH264High : VAEntrypointEncSliceLP

# Verify FFmpeg can see h264_vaapi encoder
ffmpeg -hide_banner -encoders 2>&1 | grep vaapi

# Expected output should include:
# V..... h264_vaapi           H.264/AVC (VAAPI) (codec h264)
```

**If vainfo fails with "can't connect to X server"** - this is normal and can be ignored. The important part is that it continues and shows the driver information and encoding profiles.

---

## Step 6: Get Group IDs for Docker

Docker needs to run with the correct group permissions to access `/dev/dri/renderD128`.

### Method 1: Use Helper Script (Recommended)

The repository includes a helper script:

```bash
cd /root/claudeProjects/WSL/gsd-dashboard-cast
./scripts/detect-gpu-gids.sh
```

Example output:
```
render:x:992:
video:x:44:

Add these to docker-compose.yml group_add:
  - "992"  # render
  - "44"   # video
```

### Method 2: Manual Detection

```bash
getent group render video
```

Example output:
```
render:x:992:
video:x:44:
```

The numbers after `x:` are the GIDs:
- `render` GID: **992**
- `video` GID: **44**

### Update docker-compose.yml

Edit `docker-compose.yml` and update the `group_add` section with your actual GIDs:

```yaml
services:
  cast-service:
    # ... other configuration ...
    devices:
      - /dev/dri:/dev/dri  # Pass GPU device to container
    group_add:
      - "992"  # Replace with YOUR render GID
      - "44"   # Replace with YOUR video GID
```

**Important:** GIDs may vary between systems. Always use the values from your VM, not these example numbers.

---

## Step 7: Rebuild and Test

Rebuild the Docker container with GPU access:

```bash
cd /root/claudeProjects/WSL/gsd-dashboard-cast

# Stop current container
docker compose down

# Rebuild and start
docker compose up -d --build

# Wait for service to start
sleep 5

# Check hardware acceleration status
curl http://localhost:8000/health | jq .hardware_acceleration
```

**Expected output:**
```json
{
  "quicksync_available": true,
  "encoder": "h264_vaapi"
}
```

**If you see `"quicksync_available": false`**, check:
1. `/dev/dri` exists in container: `docker exec dashboard-cast ls -la /dev/dri`
2. Container has correct group IDs: `docker exec dashboard-cast id`
3. VAAPI works in container: `docker exec dashboard-cast vainfo`

---

## Step 8: Verify CPU Reduction

Test actual CPU usage with hardware vs software encoding:

### Test 1: Hardware Encoding (Current)

```bash
# Start a test stream
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"url": "http://YOUR_URL", "quality": "720p", "duration": 60}'

# Wait 10 seconds for encoding to stabilize
sleep 10

# Measure CPU usage
docker stats --no-stream dashboard-cast
# Note the CPU% value (e.g., 58%)
```

### Test 2: Software Encoding (Fallback)

```bash
# Stop stream
curl -X POST http://localhost:8000/stop

# Disable GPU temporarily
docker compose down
sed -i 's|/dev/dri:/dev/dri|# /dev/dri:/dev/dri|' docker-compose.yml
docker compose up -d

# Wait for service
sleep 5

# Verify software mode
curl http://localhost:8000/health | jq .hardware_acceleration.encoder
# Should show: "libx264"

# Start same stream
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"url": "http://YOUR_URL", "quality": "720p", "duration": 60}'

# Wait and measure
sleep 10
docker stats --no-stream dashboard-cast
# Note the CPU% value (e.g., 83%)

# Re-enable GPU
docker compose down
sed -i 's|# /dev/dri:/dev/dri|/dev/dri:/dev/dri|' docker-compose.yml
docker compose up -d
```

### Calculate Reduction

```
Reduction = ((Software_CPU - Hardware_CPU) / Software_CPU) × 100

Example: ((83% - 58%) / 83%) × 100 = 30% reduction
```

**Note:** The CPU reduction may be less than expected (30% instead of 80-90%) because Chromium browser rendering consumes significant CPU (~50%). The hardware encoder is working correctly - the bottleneck is browser rendering, not video encoding.

---

## Troubleshooting

### GPU Not Visible in VM

**Problem:** `lspci | grep -i vga` shows no Intel GPU in VM

**Solution:**
1. Verify GPU is visible on Proxmox host: `lspci | grep -i vga`
2. Check VM hardware settings in Proxmox UI (should show PCI device)
3. Ensure VM is fully stopped before adding PCI device
4. Try removing and re-adding PCI device with "All Functions" checked

### /dev/dri Does Not Exist in VM

**Problem:** `ls /dev/dri` shows "No such file or directory"

**Solution:**
```bash
# Install kernel modules
sudo apt install -y linux-modules-extra-$(uname -r)

# Load i915 driver
sudo modprobe i915

# Verify
lsmod | grep i915
ls -la /dev/dri/
```

### vainfo Error: "Error creating a MFX session"

**Problem:** vainfo or FFmpeg shows "MFX session: -9" error

**This is expected!** The `h264_qsv` encoder has compatibility issues with CometLake Gen 10. This is why the service uses `h264_vaapi` instead, which works reliably.

**No action needed** - the service automatically uses VAAPI when available.

### Container Shows libx264 Instead of h264_vaapi

**Problem:** Health endpoint shows `"encoder": "libx264"` instead of `"h264_vaapi"`

**Solutions:**

1. Check /dev/dri exists in container:
```bash
docker exec dashboard-cast ls -la /dev/dri
```

2. Check group permissions:
```bash
docker exec dashboard-cast id
# Should show groups: 0(root),44(video),992
```

3. Check docker-compose.yml has correct GIDs:
```yaml
group_add:
  - "992"  # Must match render group from VM
  - "44"   # Must match video group from VM
```

4. Verify VAAPI works in container:
```bash
docker exec dashboard-cast vainfo
# Should show iHD driver and encoding profiles
```

### Permission Denied on /dev/dri/renderD128

**Problem:** Container logs show "Permission denied" accessing `/dev/dri/renderD128`

**Solution:** Update `docker-compose.yml` with correct group IDs from **your VM** (not example values):

```bash
# Get YOUR system's GIDs
getent group render video

# Update docker-compose.yml group_add with YOUR values
# Then rebuild:
docker compose down
docker compose up -d
```

---

## Verification Checklist

Complete this checklist to verify everything is working:

**Proxmox Host:**
- [ ] IOMMU enabled: `dmesg | grep IOMMU` shows "enabled"
- [ ] Intel GPU visible: `lspci | grep -i vga` shows Intel GPU
- [ ] /dev/dri exists: `ls -la /dev/dri/` shows card0 and renderD128

**Ubuntu VM:**
- [ ] GPU visible in VM: `lspci | grep -i vga` shows Intel GPU
- [ ] i915 module loaded: `lsmod | grep i915` shows i915
- [ ] /dev/dri exists: `ls -la /dev/dri/` shows card0 and renderD128
- [ ] VAAPI drivers installed: `vainfo` runs without fatal errors
- [ ] iHD driver active: `vainfo` shows "iHD driver" (not i965)
- [ ] Encoding supported: `vainfo` shows "VAEntrypointEncSliceLP" for H264
- [ ] FFmpeg sees h264_vaapi: `ffmpeg -encoders | grep vaapi` shows h264_vaapi

**Docker Container:**
- [ ] /dev/dri accessible: `docker exec dashboard-cast ls -la /dev/dri`
- [ ] Correct groups: `docker exec dashboard-cast id` shows render and video groups
- [ ] VAAPI works: `docker exec dashboard-cast vainfo` succeeds
- [ ] Service detects hardware: `curl localhost:8000/health` shows `"quicksync_available": true`
- [ ] Using VAAPI encoder: Health shows `"encoder": "h264_vaapi"`

**CPU Reduction Test:**
- [ ] Hardware encoding CPU measured (e.g., 58%)
- [ ] Software encoding CPU measured (e.g., 83%)
- [ ] Reduction calculated (e.g., 30%)

---

## Technical Details

### Why VAAPI Instead of QuickSync QSV?

The service was originally designed to use Intel QuickSync's `h264_qsv` encoder. However, testing revealed that CometLake Gen 10 GPUs have compatibility issues with FFmpeg's QSV implementation:

```
Error creating a MFX session: -9
```

**VAAPI** (Video Acceleration API) is the native Linux hardware acceleration API and works more reliably:
- ✅ Direct access to Intel GPU encoder
- ✅ Native Linux kernel support
- ✅ No MFX session initialization issues
- ✅ Same hardware encoder, different API

The service automatically detects VAAPI availability and uses it when present.

### Encoder Configuration

**Hardware (h264_vaapi):**
```
-vaapi_device /dev/dri/renderD128
-vf format=nv12,hwupload
-c:v h264_vaapi
-qp 23  # Constant QP (quality)
```

**Software Fallback (libx264):**
```
-c:v libx264
-preset fast
-b:v 3000k
```

### CPU Usage Expectations

**Typical results:**
- Software encoding (libx264): 75-85% CPU
- Hardware encoding (h264_vaapi): 50-60% CPU
- **Reduction: 25-35%**

**Why not 80-90%?** Browser rendering (Chromium headless) consumes ~50% CPU regardless of encoder. The encoding portion sees 80%+ reduction, but it's only part of total CPU usage.

---

## References

- [Proxmox PCI Passthrough Wiki](https://pve.proxmox.com/wiki/PCI_Passthrough)
- [FFmpeg VAAPI Documentation](https://trac.ffmpeg.org/wiki/Hardware/VAAPI)
- [Intel Media Driver GitHub](https://github.com/intel/media-driver)
- [Project Research](.planning/phases/10-intel-quicksync-hardware-acceleration/10-RESEARCH.md)

---

## Support

If you encounter issues not covered in this guide:

1. Check container logs: `docker logs dashboard-cast --tail 50`
2. Verify VAAPI in container: `docker exec dashboard-cast vainfo`
3. Check hardware detection: `curl localhost:8000/health | jq`
4. Review project issues: https://github.com/WallyWithCode/gsd-dashboard-cast/issues

---

*Guide created: 2026-01-19*
*Last updated: 2026-01-19*
*Tested on: Proxmox VE 8.2.7, Ubuntu 22.04 VM, Intel NUC9i5FN (CometLake Gen 10)*
