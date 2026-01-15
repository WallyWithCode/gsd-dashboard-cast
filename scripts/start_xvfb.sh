#!/bin/bash
# Start Xvfb virtual display for video capture

set -e

DISPLAY="${DISPLAY:-:99}"
RESOLUTION="${XVFB_RESOLUTION:-1920x1080}"
DEPTH="${XVFB_DEPTH:-24}"

echo "Starting Xvfb on display $DISPLAY with resolution ${RESOLUTION}x${DEPTH}"

# Start Xvfb in background
Xvfb "$DISPLAY" -screen 0 "${RESOLUTION}x${DEPTH}" -ac -nolisten tcp &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 2

# Verify Xvfb is running
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "ERROR: Xvfb failed to start"
    exit 1
fi

echo "Xvfb started successfully (PID: $XVFB_PID)"

# Keep script running to maintain Xvfb process
wait $XVFB_PID
