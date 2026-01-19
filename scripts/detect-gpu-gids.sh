#!/bin/bash
# Detect render and video group IDs for GPU passthrough
echo "Detecting GPU device group IDs..."
echo ""
RENDER_GID=$(getent group render 2>/dev/null | cut -d: -f3)
VIDEO_GID=$(getent group video 2>/dev/null | cut -d: -f3)

if [ -z "$RENDER_GID" ]; then
  echo "WARNING: render group not found"
else
  echo "RENDER_GID: $RENDER_GID"
fi

if [ -z "$VIDEO_GID" ]; then
  echo "WARNING: video group not found"
else
  echo "VIDEO_GID: $VIDEO_GID"
fi

echo ""
echo "Update docker-compose.yml group_add section with these values:"
echo "    group_add:"
echo "      - \"${RENDER_GID:-RENDER_GID_NOT_FOUND}\""
echo "      - \"${VIDEO_GID:-VIDEO_GID_NOT_FOUND}\""
