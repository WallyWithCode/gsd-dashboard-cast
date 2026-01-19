FROM python:3.11-slim as base

# Install system dependencies for Playwright, FFmpeg, Intel QuickSync, and Xvfb
RUN apt-get update && \
    apt-get install -y \
    wget \
    gnupg \
    ffmpeg \
    xvfb \
    intel-media-va-driver \
    vainfo \
    libva2 \
    libva-drm2 \
    && rm -rf /var/lib/apt/lists/*

# Verify FFmpeg 7.0+ with OneVPL support and h264_qsv encoder availability
RUN ffmpeg_version=$(ffmpeg -version | head -1 | grep -oP 'ffmpeg version \K[0-9]+\.[0-9]+' || echo "0.0") && \
    major_version=$(echo "$ffmpeg_version" | cut -d. -f1) && \
    echo "FFmpeg version: $ffmpeg_version (major: $major_version)" && \
    if [ "$major_version" -lt 7 ]; then \
        echo "ERROR: FFmpeg 7.0+ required for OneVPL support (found: $ffmpeg_version)"; \
        exit 1; \
    fi && \
    ffmpeg -encoders 2>/dev/null | grep h264_qsv || echo "WARNING: h264_qsv not found - hardware acceleration unavailable"

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser and system dependencies
# playwright install-deps installs OS-level dependencies (libglib, libnss, etc.) that Chrome requires
# Without this, browser launch fails
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application source code
COPY src/ ./src/

# Run the application
CMD ["python", "-m", "src.main"]
