FROM python:3.11-slim as base

# Install system dependencies for Playwright, FFmpeg, and Xvfb
RUN apt-get update && \
    apt-get install -y wget gnupg ffmpeg xvfb && \
    rm -rf /var/lib/apt/lists/*

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
