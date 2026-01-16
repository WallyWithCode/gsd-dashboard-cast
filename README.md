# Dashboard Cast Service

A Docker service that receives webhook requests to render live webpages (dashboards, camera feeds) as video streams and casts them to Android TV devices. Designed for smart home automation, particularly Home Assistant integrations, with webhook-based start/stop control.

## Overview

The Dashboard Cast Service enables Home Assistant automations to display contextual information on your Android TV on demand. When triggered by events (doorbell rings, motion detected, etc.), it renders authenticated web dashboards as live video streams and casts them to your TV.

**Key Features:**
- Webhook-triggered casting (start/stop via HTTP API)
- Supports authenticated dashboards (cookies and tokens)
- Configurable video quality presets
- Automatic HDMI-CEC TV wake
- Continuous streaming until explicitly stopped
- Docker deployment with minimal setup

## Requirements

- **Docker** and **Docker Compose**
- **Cast-enabled Android TV** on local network
- **Dashboards** accessible on local network (Home Assistant, Frigate, etc.)

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd gsd-dashboard-cast
   ```

2. **Configure environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env if you need to set CAST_DEVICE_IP or CAST_DEVICE_NAME
   ```

3. **Start the service:**
   ```bash
   docker-compose up -d
   ```

4. **Test with curl:**
   ```bash
   curl -X POST http://localhost:8000/start \
     -H "Content-Type: application/json" \
     -d '{"url": "http://homeassistant.local:8123/dashboard"}'
   ```

The service is now running and ready to receive webhook requests.

## Environment Variables

The service uses environment variables for configuration. See `.env.example` for a complete list.

### Required Variables (Auto-configured in Docker)

| Variable | Default | Description |
|----------|---------|-------------|
| `DISPLAY` | `:99` | Virtual display for Xvfb (managed automatically) |
| `PYTHONUNBUFFERED` | `1` | Enable real-time log streaming |

### Optional Variables (Cast Device Configuration)

| Variable | Description | Example |
|----------|-------------|---------|
| `CAST_DEVICE_IP` | Static IP address for Cast device (bypasses mDNS discovery) | `10.10.0.31` |
| `CAST_DEVICE_NAME` | Friendly name of Cast device to discover | `"Living Room TV"` |

**Note:** If both are set, `CAST_DEVICE_IP` takes precedence.

## API Endpoints

### POST /start - Start Casting

Start casting a URL to your Android TV.

**Request:**
```json
{
  "url": "http://homeassistant.local:8123/dashboard",
  "quality": "1080p",
  "duration": null
}
```

**Parameters:**
- `url` (required): URL to cast (must be HTTP or HTTPS)
- `quality` (optional): Quality preset - `1080p` (default), `720p`, or `low-latency`
- `duration` (optional): Streaming duration in seconds, `null` for indefinite (default)

**Response:**
```json
{
  "status": "success",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Behavior:**
- Returns immediately (streaming runs in background)
- Automatically stops any previous stream before starting new one
- Wakes TV via HDMI-CEC before casting

### POST /stop - Stop Casting

Stop the active casting session.

**Response:**
```json
{
  "status": "success",
  "message": "Stream stopped"
}
```

### GET /status - Check Status

Check if a stream is currently active.

**Response (idle):**
```json
{
  "status": "idle",
  "stream": null
}
```

**Response (casting):**
```json
{
  "status": "casting",
  "stream": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### GET /health - Service Health

Check service health and Cast device availability.

**Response:**
```json
{
  "status": "healthy",
  "active_streams": 1,
  "cast_device": "available"
}
```

**Status values:**
- `healthy`: Service operational and Cast device discoverable
- `degraded`: Service operational but Cast device unavailable

## Testing with curl

### Start casting a dashboard
```bash
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://homeassistant.local:8123/dashboard",
    "quality": "1080p"
  }'
```

### Start casting with custom duration (60 seconds)
```bash
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://homeassistant.local:8123/dashboard",
    "quality": "720p",
    "duration": 60
  }'
```

### Stop casting
```bash
curl -X POST http://localhost:8000/stop
```

### Check status
```bash
curl http://localhost:8000/status
```

### Check health
```bash
curl http://localhost:8000/health
```

## Quality Presets

The service supports three quality presets optimized for different use cases:

| Preset | Resolution | Bitrate | FPS | Use Case |
|--------|-----------|---------|-----|----------|
| `1080p` | 1920x1080 | 5000 kbps | 30 | High-quality dashboards (default) |
| `720p` | 1280x720 | 2500 kbps | 30 | Balanced quality and bandwidth |
| `low-latency` | 1280x720 | 2000 kbps | 30 | Minimal encoding delay |

**Example:**
```bash
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"url": "http://192.168.1.100:8123/dashboard", "quality": "low-latency"}'
```

## WSL2 Limitation

**Known Issue:** Cast device discovery via mDNS does not work in WSL2/Docker environments because multicast packets don't forward through WSL2's virtualized NAT network.

**Workaround:** Use the `CAST_DEVICE_IP` environment variable to specify your Cast device's static IP address:

1. Find your Cast device's IP address:
   - Check your Cast device settings
   - Or check your router's DHCP leases

2. Set the environment variable:
   ```bash
   echo "CAST_DEVICE_IP=10.10.0.31" >> .env
   docker-compose restart
   ```

This limitation only affects WSL2 environments. On native Linux, macOS, or Windows, mDNS discovery works normally.

## Security Considerations

**HTTP URL Support:** The service accepts HTTP URLs (not just HTTPS) to support local network dashboards that typically don't use SSL. This is appropriate for:

- Home Assistant dashboards on local network
- IP camera feeds on local network
- Other local services without HTTPS

**Important:** Only cast URLs you trust. The service will render and stream whatever content is at the provided URL. For local network use (the intended use case), this is not a security concern. If exposing the API outside your local network, implement additional authentication and URL validation.

## Home Assistant Integration

### Basic Automation Example

Trigger dashboard display when doorbell is pressed:

```yaml
automation:
  - alias: "Show Door Camera on TV"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      - service: rest_command.cast_dashboard
        data:
          url: "http://192.168.1.100:8123/lovelace/cameras"
          quality: "1080p"
```

### REST Command Configuration

Add to your `configuration.yaml`:

```yaml
rest_command:
  cast_dashboard:
    url: http://your-server-ip:8000/start
    method: POST
    content_type: "application/json"
    payload: '{"url": "{{ url }}", "quality": "{{ quality }}"}'

  stop_cast:
    url: http://your-server-ip:8000/stop
    method: POST
```

### Advanced Example with Auto-Stop

Show camera for 30 seconds, then return to normal dashboard:

```yaml
automation:
  - alias: "Show Door Camera Temporarily"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      # Show camera feed
      - service: rest_command.cast_dashboard
        data:
          url: "http://192.168.1.100:8123/lovelace/cameras"
          quality: "1080p"
      # Wait 30 seconds
      - delay:
          seconds: 30
      # Return to main dashboard
      - service: rest_command.cast_dashboard
        data:
          url: "http://192.168.1.100:8123/lovelace/default"
          quality: "1080p"
```

## Logs

View service logs:
```bash
docker-compose logs -f cast-service
```

The service uses structured JSON logging for easy parsing and monitoring.

## Troubleshooting

### Cast device not found

**Symptoms:** Health check shows `"cast_device": "unavailable"`

**Solutions:**
1. Verify Cast device is on and connected to same network
2. Check `docker-compose.yml` has `network_mode: host` (required for mDNS)
3. If using WSL2, set `CAST_DEVICE_IP` environment variable (see WSL2 Limitation section)

### Service not starting

**Check logs:**
```bash
docker-compose logs cast-service
```

**Common issues:**
- Port 8000 already in use (change in `docker-compose.yml`)
- Insufficient shared memory (check `shm_size: 2gb` in `docker-compose.yml`)

### Stream not appearing on TV

**Verify:**
1. Check `/status` endpoint shows `"status": "casting"`
2. Check TV is on and not in power-saving mode
3. Try stopping and starting the stream again
4. Check service logs for errors

## Development

### Running without Docker

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install system dependencies:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install xvfb ffmpeg chromium-browser
   ```

3. Run the service:
   ```bash
   python src/main.py
   ```

### Running tests

```bash
pytest tests/
```

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
