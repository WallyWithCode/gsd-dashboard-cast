# Proxmox Intel GPU Hardware Acceleration Guide

## Overview

This guide enables Intel GPU hardware acceleration for the Dashboard Cast Service running in Proxmox VMs. Hardware acceleration offloads H.264 encoding from CPU to GPU, significantly reducing CPU usage during streaming.

**Important:** This guide uses **VAAPI** (Video Acceleration API), not Intel QuickSync QSV directly. Testing revealed that `h264_qsv` has compatibility issues on some Intel GPU generations (MFX session initialization errors), while `h264_vaapi` works reliably across all supported hardware.

**Requirements:**
- Proxmox VE 7.0+
- Intel CPU with integrated graphics (NOT "F" suffix models like i9-14900KF)
- Intel Gen 8+ CPU (Coffee Lake 2017+) recommended for best iHD driver support
- Ubuntu VM with kernel 5.15+ (or Debian-based distro)

**Tested Hardware:**
- Intel Gen 8-12 CPUs (Coffee Lake, Comet Lake, Ice Lake, Tiger Lake, Alder Lake)
- Proxmox VE 7.x and 8.x
- Ubuntu 20.04, 22.04, 24.04
- Debian 11, 12

**Expected Results:**
- CPU reduction: 20-40% (varies based on workload)
- Hardware encoder offloads encoding, but browser rendering remains on CPU
- Greater reduction with multiple simultaneous streams

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
# Should show: Intel Corporation [GPU model name]

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
00:02.0 VGA compatible controller: Intel Corporation CometLake-U GT2 [UHD Graphics]
```

Note the PCI address (e.g., `00:02.0`) - **yours will likely be different**.

### Add GPU to VM via Proxmox Web UI

1. **Stop your VM** (must be powered off before adding PCI device)

2. In Proxmox web UI:
   - Select your VM (e.g., VM 100, 103, etc.)
   - Go to **Hardware** tab
   - Click **Add** → **PCI Device**

3. Configure PCI device:
   - **Device:** Select your Intel GPU (look for "VGA compatible controller: Intel")
   - ✅ **All Functions** (check this box)
   - ✅ **Primary GPU** (check this if it's the only/main GPU)
   - **ROM-Bar:** Leave enabled (default)
   - **PCI-Express:** Leave enabled (default)

4. Click **Add**

5. **Start your VM**

### Verify GPU is Visible in VM

SSH into your Ubuntu VM and check:

```bash
lspci | grep -i vga
```

You should see the Intel GPU. The PCI address in the VM may differ from the host:
```
00:10.0 VGA compatible controller: Intel Corporation [Your GPU Model]
```

✅ **If you see the Intel GPU, passthrough is working!** Proceed to Step 3.

❌ **If GPU is not visible**, see troubleshooting section.

---

## Step 3: Install Kernel Modules (Ubuntu VM)

The Intel graphics driver (`i915`) is not included in the base kernel package.

```bash
# Install extra kernel modules for your current kernel
sudo apt update
sudo apt install -y linux-modules-extra-$(uname -r)

# Load the i915 module
sudo modprobe i915

# Verify module is loaded
lsmod | grep i915
# Should show i915 and related modules (drm, video, etc.)

# Make module load automatically at boot
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

**Important:** Note the group ownership:
- `card0` → owned by `video` group
- `renderD128` → owned by `render` group

These group names are standard, but the **GID numbers** vary between systems.

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

**Package notes:**
- `intel-media-va-driver`: Modern iHD driver for Gen 8+ GPUs
- `i965-va-driver`: Legacy driver for Gen 4-7 GPUs (still useful for fallback)
- Use the standard package name (no `-non-free` suffix needed on Ubuntu/Debian)

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

**If vainfo shows "can't connect to X server"** - this is normal and can be ignored. The important part is that it continues and shows the driver information and encoding profiles.

✅ **Success indicators:**
- `va_openDriver() returns 0` (driver loaded)
- Driver shows "iHD" (modern driver)
- `VAEntrypointEncSliceLP` listed for H264 profiles (hardware encoding supported)

---

## Step 6: Get Group IDs for Docker

Docker needs to run with the correct group permissions to access `/dev/dri/renderD128`.

**Important:** Group IDs (GIDs) **vary between systems**. You must get the values from **your specific VM**.

### Method 1: Use Helper Script (Recommended)

The repository includes a helper script:

```bash
cd /path/to/gsd-dashboard-cast
./scripts/detect-gpu-gids.sh
```

Example output:
```
render:x:109:
video:x:44:

Add these to docker-compose.yml group_add:
  - "109"  # render
  - "44"   # video
```

**Your numbers will likely be different!**

### Method 2: Manual Detection

```bash
getent group render video
```

Example output:
```
render:x:109:
video:x:44:
```

The numbers after `x:` are the GIDs. In this example:
- `render` GID: **109**
- `video` GID: **44**

**Record your actual GID values** - you'll need them for the next step.

### Update docker-compose.yml

Edit `docker-compose.yml` and update the `group_add` section:

```yaml
services:
  cast-service:
    # ... other configuration ...
    devices:
      - /dev/dri:/dev/dri  # Pass GPU device to container
    group_add:
      - "YOUR_RENDER_GID"  # Replace with YOUR render GID (e.g., "109")
      - "YOUR_VIDEO_GID"   # Replace with YOUR video GID (e.g., "44")
```

**Example (DO NOT copy these numbers, use your own!):**
```yaml
    group_add:
      - "109"  # render GID from YOUR system
      - "44"   # video GID from YOUR system
```

**⚠️ Warning:** Do not use example values! These GIDs are specific to each system. Using wrong values will cause "Permission denied" errors.

---

## Step 7: Rebuild and Test

Rebuild the Docker container with GPU access:

```bash
cd /path/to/gsd-dashboard-cast

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

✅ **Success!** Hardware acceleration is enabled.

**If you see `"quicksync_available": false`**, see troubleshooting section below.

---

## Step 8: Verify CPU Reduction (Optional)

Test actual CPU usage with hardware vs software encoding to confirm benefit.

### Test 1: Hardware Encoding (Current)

```bash
# Start a test stream (replace with your actual URL)
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-dashboard-url.com", "quality": "720p", "duration": 60}'

# Wait 10 seconds for encoding to stabilize
sleep 10

# Measure CPU usage
docker stats --no-stream dashboard-cast
```

**Record the CPU% value.** Example: `58.5%`

### Test 2: Software Encoding (Fallback)

```bash
# Stop stream
curl -X POST http://localhost:8000/stop

# Temporarily disable GPU
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
  -d '{"url": "https://your-dashboard-url.com", "quality": "720p", "duration": 60}'

# Wait and measure
sleep 10
docker stats --no-stream dashboard-cast
```

**Record the CPU% value.** Example: `82.3%`

### Re-enable GPU

```bash
docker compose down
sed -i 's|# /dev/dri:/dev/dri|/dev/dri:/dev/dri|' docker-compose.yml
docker compose up -d
```

### Calculate Reduction

```
CPU_Reduction = ((Software_CPU - Hardware_CPU) / Software_CPU) × 100

Example: ((82.3 - 58.5) / 82.3) × 100 = 28.9% reduction
```

**Typical reductions: 20-40%**

The reduction varies based on workload complexity and resolution. Browser rendering consumes significant CPU (~40-50%) regardless of encoder, so total reduction is less than the encoding-only reduction (which can be 70-90%).

---

## Troubleshooting

### GPU Not Visible in VM

**Symptom:** `lspci | grep -i vga` shows no Intel GPU in VM

**Solutions:**
1. Verify GPU is visible on Proxmox host: `lspci | grep -i vga`
2. Check VM hardware settings in Proxmox UI (should show PCI device in Hardware tab)
3. Ensure VM was **fully stopped** before adding PCI device (not just paused)
4. Try removing and re-adding PCI device with "All Functions" checked
5. Some BIOS settings may disable iGPU when discrete GPU present - check BIOS

### /dev/dri Does Not Exist in VM

**Symptom:** `ls /dev/dri` shows "No such file or directory"

**Solution:**
```bash
# Install kernel modules
sudo apt install -y linux-modules-extra-$(uname -r)

# Load i915 driver
sudo modprobe i915

# Verify
lsmod | grep i915  # Should show i915 module loaded
ls -la /dev/dri/   # Should show card0 and renderD128
```

### vainfo Error: "Error creating a MFX session"

**Symptom:** vainfo or FFmpeg shows "MFX session: -9" error

**This is expected!** The `h264_qsv` encoder has compatibility issues on some Intel GPU generations. This is why the service uses `h264_vaapi` instead, which works reliably.

**No action needed** - the service automatically uses VAAPI when available.

### Container Shows libx264 Instead of h264_vaapi

**Symptom:** Health endpoint shows `"encoder": "libx264"` instead of `"h264_vaapi"`

**Diagnostic steps:**

1. Check /dev/dri exists in container:
```bash
docker exec dashboard-cast ls -la /dev/dri
# Should show card0 and renderD128
```

2. Check group permissions:
```bash
docker exec dashboard-cast id
# Should show groups including render and video GIDs
```

3. Verify docker-compose.yml has **correct GIDs from your system**:
```bash
# Get YOUR system's GIDs
getent group render video

# Update docker-compose.yml group_add with YOUR values
```

4. Verify VAAPI works in container:
```bash
docker exec dashboard-cast vainfo
# Should show iHD driver and encoding profiles
```

5. Check container logs for errors:
```bash
docker logs dashboard-cast --tail 50 | grep -i "vaapi\|hardware\|qsv"
```

### Permission Denied on /dev/dri/renderD128

**Symptom:** Container logs show "Permission denied" accessing `/dev/dri/renderD128`

**Root cause:** Wrong group IDs in docker-compose.yml

**Solution:**
```bash
# Get YOUR system's actual GIDs (don't use example values!)
getent group render video

# Example output:
# render:x:109:
# video:x:44:

# Update docker-compose.yml group_add with YOUR numbers:
services:
  cast-service:
    group_add:
      - "109"  # YOUR render GID
      - "44"   # YOUR video GID

# Rebuild container
docker compose down
docker compose up -d
```

### Wrong Driver (i965 Instead of iHD)

**Symptom:** `vainfo` shows "i965" driver instead of "iHD"

**Issue:** Legacy driver being used instead of modern driver

**Solution:**
```bash
# Force iHD driver in docker-compose.yml
services:
  cast-service:
    environment:
      - LIBVA_DRIVER_NAME=iHD

# Rebuild
docker compose down
docker compose up -d

# Verify
docker exec dashboard-cast vainfo | grep "Driver version"
# Should show: Driver version: Intel iHD driver
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

**CPU Reduction Test (Optional):**
- [ ] Hardware encoding CPU measured
- [ ] Software encoding CPU measured
- [ ] Reduction calculated (typically 20-40%)

---

## Technical Details

### Why VAAPI Instead of QuickSync QSV?

The service was originally designed to use Intel QuickSync's `h264_qsv` encoder. However, testing revealed compatibility issues with FFmpeg's QSV implementation on some Intel GPU generations:

```
Error creating a MFX session: -9
```

**VAAPI** (Video Acceleration API) is the native Linux hardware acceleration API and works more reliably:
- ✅ Direct access to Intel GPU encoder
- ✅ Native Linux kernel support via i915 driver
- ✅ No MFX session initialization issues
- ✅ Same underlying hardware encoder, different software interface
- ✅ Better compatibility across Intel GPU generations

The service automatically detects VAAPI availability and uses it when present, falling back to software encoding (libx264) if hardware is unavailable.

### Encoder Configuration

**Hardware (h264_vaapi):**
```bash
-vaapi_device /dev/dri/renderD128  # Select GPU render node
-vf format=nv12,hwupload           # Upload frames to GPU memory
-c:v h264_vaapi                    # Use VAAPI H.264 encoder
-qp 23                             # Constant QP (quality factor)
```

**Software Fallback (libx264):**
```bash
-c:v libx264       # Software H.264 encoder
-preset fast       # Encoding speed preset
-b:v 3000k         # Bitrate (varies by quality preset)
```

The service automatically selects the appropriate encoder based on hardware availability.

### CPU Usage Expectations

**Typical results:**
- Software encoding (libx264): **70-85% CPU**
- Hardware encoding (h264_vaapi): **50-65% CPU**
- **Reduction: 20-40%**

**Why not 80-90% reduction?**

Browser rendering (Chromium headless) consumes 40-50% CPU regardless of encoder choice. The encoding portion itself sees 70-90% reduction, but it's only part of the total workload:

```
Total CPU = Browser Rendering (40-50%) + Video Encoding (20-40%)

Hardware: 50% browser + 5-10% encoding = 55-60% total
Software: 50% browser + 20-35% encoding = 70-85% total

Reduction: ~30% overall (but 70-90% for encoding portion)
```

The benefit increases with:
- Multiple simultaneous streams (encoding scales, rendering doesn't)
- Higher resolutions (1080p vs 720p)
- Higher frame rates (30fps vs 15fps)

---

## References

- [Proxmox PCI Passthrough Wiki](https://pve.proxmox.com/wiki/PCI_Passthrough)
- [FFmpeg VAAPI Documentation](https://trac.ffmpeg.org/wiki/Hardware/VAAPI)
- [Intel Media Driver GitHub](https://github.com/intel/media-driver)
- [Linux i915 Driver Documentation](https://www.kernel.org/doc/html/latest/gpu/i915.html)

---

## Support

If you encounter issues not covered in this guide:

1. **Check container logs:** `docker logs dashboard-cast --tail 50`
2. **Verify VAAPI in container:** `docker exec dashboard-cast vainfo`
3. **Check hardware detection:** `curl localhost:8000/health | jq`
4. **Search existing issues:** https://github.com/WallyWithCode/gsd-dashboard-cast/issues
5. **Open new issue** with:
   - Output of verification checklist commands
   - Container logs
   - Your Intel GPU model (`lspci | grep -i vga`)

---

*Guide created: 2026-01-19*
*Last updated: 2026-01-19*
*Tested on: Proxmox VE 7.x/8.x, Ubuntu 20.04-24.04, Intel Gen 8-12 GPUs*
