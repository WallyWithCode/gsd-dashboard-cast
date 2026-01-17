# v1.1 HTTP Video Streaming Stack Research

> Research Date: 2026-01-16
> Domain: HTTP video streaming (HLS and fMP4) for Python Cast application
> Purpose: Identify libraries/tools needed to serve video streams via HTTP to Cast devices

---

## Executive Summary

For v1.1 Cast Media Playback, the recommended approach is to **extend the existing FastAPI application** with streaming endpoints rather than adding a separate aiohttp server. FastAPI natively supports video streaming through `StreamingResponse` and file serving via `FileResponse`. For HLS, FFmpeg handles segment generation directly; Python's role is serving segments and managing playlists dynamically with the `m3u8` library.

**Key Recommendations**:
1. Use FastAPI's `StreamingResponse` for serving HLS/fMP4 content (no aiohttp needed)
2. Use `m3u8>=6.0.0` library for playlist generation/parsing
3. FFmpeg handles all transcoding - use different output flags for HLS vs fMP4
4. Add `aiofiles>=24.1.0` for async file I/O when serving segments

---

## 1. Recommended Stack Additions

### 1.1 New Dependencies

| Package | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| `m3u8` | `>=6.0.0` | HLS playlist generation and parsing | HIGH |
| `aiofiles` | `>=24.1.0` | Async file I/O for segment serving | HIGH |

### 1.2 Existing Stack (v1.0)

```
playwright>=1.40.0       # Browser automation
pytest>=8.0.0            # Testing
pytest-asyncio>=0.23.0   # Async test support
pychromecast>=13.0.0     # Cast protocol
fastapi>=0.115.0         # HTTP API framework
uvicorn>=0.32.0          # ASGI server
structlog>=25.5.0        # Structured logging
```

### 1.3 What We Do NOT Need

| Library | Reason Not Needed |
|---------|-------------------|
| `aiohttp` (as server) | FastAPI already provides async HTTP serving |
| `ffmpeg-python` | Direct subprocess calls are simpler and more flexible |
| `python-hls` | FFmpeg generates segments; m3u8 handles playlists |
| Shaka Packager | FFmpeg can produce CMAF/fMP4 directly |

**Source**: [FastAPI vs aiohttp comparison](https://likegeeks.com/fastapi-vs-aiohttp/) - HIGH confidence

---

## 2. Library Details and Rationale

### 2.1 m3u8 Library (globocom/m3u8)

**Version**: 6.0.0 (released August 7, 2024)
**License**: MIT
**Python**: >=3.7

**Purpose**: Parse and generate M3U8 playlists for HLS streaming.

**Key Features**:
- Load playlists from URLs or files
- Programmatically create/modify playlists
- Access segments, target duration, media sequence
- Dump playlists to files or strings

**Usage Example**:
```python
import m3u8

# Create a live playlist
playlist = m3u8.M3U8()
playlist.target_duration = 6
playlist.media_sequence = 0
playlist.is_endlist = False  # Live stream

# Add segments dynamically
segment = m3u8.Segment(
    uri="segment_001.ts",
    duration=6.0
)
playlist.add_segment(segment)

# Output
playlist_content = playlist.dumps()
```

**Source**: [globocom/m3u8 GitHub](https://github.com/globocom/m3u8) - HIGH confidence
**Source**: [m3u8 on PyPI](https://pypi.org/project/m3u8/) - HIGH confidence

### 2.2 aiofiles Library

**Version**: 24.1.0 (latest stable)
**License**: Apache 2.0
**Python**: >=3.8

**Purpose**: Async file I/O for non-blocking segment serving.

**Rationale**: When serving HLS segments or fMP4 chunks, synchronous file reads can block the event loop. `aiofiles` provides async file operations that integrate with FastAPI's async handlers.

**Usage Example**:
```python
import aiofiles
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

async def stream_segment(segment_path: str):
    async with aiofiles.open(segment_path, 'rb') as f:
        while chunk := await f.read(1024 * 1024):  # 1MB chunks
            yield chunk

@app.get("/hls/{segment_name}")
async def serve_segment(segment_name: str):
    path = f"/var/streams/{segment_name}"
    return StreamingResponse(
        stream_segment(path),
        media_type="video/MP2T"
    )
```

**Source**: [aiohttp static file serving with aiofiles](https://github.com/aio-libs/aiohttp/issues/1404) - MEDIUM confidence
**Source**: [Efficiently Sending Files with aiohttp](https://proxiesapi.com/articles/efficiently-sending-files-with-aiohttp-in-python) - MEDIUM confidence

---

## 3. FFmpeg Command Differences: HLS vs fMP4

### 3.1 HLS Output (MPEG-TS Segments)

```bash
ffmpeg -f x11grab -video_size 1280x720 -framerate 30 -i :99 \
  -c:v libx264 -profile:v high -level 4.1 \
  -preset veryfast -tune zerolatency \
  -b:v 2000k -maxrate 2500k -bufsize 4000k \
  -g 180 -keyint_min 180 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 44100 \
  -f hls \
  -hls_time 6 \
  -hls_list_size 5 \
  -hls_flags delete_segments+independent_segments \
  -hls_segment_filename "/var/streams/segment_%03d.ts" \
  /var/streams/playlist.m3u8
```

**Key HLS Flags**:
| Flag | Value | Purpose |
|------|-------|---------|
| `-f hls` | - | HLS muxer output |
| `-hls_time` | `6` | Target segment duration (seconds) |
| `-hls_list_size` | `5` | Segments kept in playlist (live window) |
| `-hls_flags delete_segments` | - | Auto-delete old segments |
| `-hls_flags independent_segments` | - | Adds `#EXT-X-INDEPENDENT-SEGMENTS` |
| `-hls_segment_filename` | pattern | Segment naming pattern |
| `-g 180` | - | GOP size = 180 frames (6s @ 30fps) |
| `-sc_threshold 0` | - | Disable scene change detection |

**Source**: [OTTVerse HLS Packaging](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/) - HIGH confidence
**Source**: [FFmpeg HLS Formats Documentation](https://ffmpeg.org/ffmpeg-formats.html) - HIGH confidence

### 3.2 fMP4 Output (Fragmented MP4 for Low-Latency)

```bash
ffmpeg -f x11grab -video_size 1280x720 -framerate 30 -i :99 \
  -c:v libx264 -profile:v high -level 4.1 \
  -preset ultrafast -tune zerolatency \
  -b:v 2000k -maxrate 2500k -bufsize 2000k \
  -g 30 -keyint_min 30 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 44100 \
  -f mp4 \
  -movflags frag_keyframe+empty_moov+default_base_moof \
  -frag_duration 500000 \
  pipe:1
```

**Key fMP4 Flags**:
| Flag | Value | Purpose |
|------|-------|---------|
| `-f mp4` | - | MP4 container output |
| `-movflags frag_keyframe` | - | Fragment at every keyframe |
| `-movflags empty_moov` | - | Write `moov` box first (streaming-compatible) |
| `-movflags default_base_moof` | - | Use `moof` as base for offsets (easier parsing) |
| `-frag_duration` | `500000` | Fragment duration in microseconds (500ms) |
| `-g 30` | - | GOP size = 30 frames (1s @ 30fps for frequent keyframes) |
| `pipe:1` | - | Output to stdout for HTTP streaming |

**Source**: [MDN Transcoding for Media Source Extensions](https://developer.mozilla.org/en-US/docs/Web/API/Media_Source_Extensions_API/Transcoding_assets_for_MSE) - HIGH confidence
**Source**: [fMP4 for In-Browser Live Video](https://medium.com/@vlad.pbr/in-browser-live-video-using-fragmented-mp4-3aedb600a07e) - MEDIUM confidence

### 3.3 HLS with fMP4 Segments (CMAF)

```bash
ffmpeg -f x11grab -video_size 1280x720 -framerate 30 -i :99 \
  -c:v libx264 -profile:v high -level 4.1 \
  -preset veryfast -tune zerolatency \
  -b:v 2000k -maxrate 2500k -bufsize 4000k \
  -g 60 -keyint_min 60 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 44100 \
  -f hls \
  -hls_time 2 \
  -hls_list_size 5 \
  -hls_flags delete_segments+independent_segments \
  -hls_segment_type fmp4 \
  -hls_fmp4_init_filename "init.mp4" \
  -hls_segment_filename "/var/streams/segment_%03d.m4s" \
  /var/streams/playlist.m3u8
```

**CMAF-specific Flags**:
| Flag | Value | Purpose |
|------|-------|---------|
| `-hls_segment_type fmp4` | - | Use fMP4 instead of MPEG-TS |
| `-hls_fmp4_init_filename` | `init.mp4` | Initialization segment name |

**Note**: CMAF/fMP4 HLS requires `useShakaForHls: true` on Cast devices. The default Media Player Library does not support fMP4 HLS containers.

**Source**: [Unified Streaming fMP4 HLS](https://docs.unified-streaming.com/documentation/package/fmp4-hls.html) - HIGH confidence

---

## 4. FastAPI Integration Pattern

### 4.1 No Separate aiohttp Server Needed

FastAPI (built on Starlette) provides all required streaming capabilities:
- `StreamingResponse` for chunked streaming
- `FileResponse` for static segment serving
- Native async/await support
- Lifespan events for resource management

**Source**: [FastAPI Custom Response Documentation](https://fastapi.tiangolo.com/advanced/custom-response/) - HIGH confidence

### 4.2 Recommended Integration Architecture

```python
# src/api/streaming.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
import aiofiles
import m3u8
from pathlib import Path

router = APIRouter(prefix="/stream", tags=["streaming"])

STREAM_DIR = Path("/var/streams")

@router.get("/{stream_id}/playlist.m3u8")
async def get_playlist(stream_id: str):
    """Serve HLS playlist."""
    playlist_path = STREAM_DIR / stream_id / "playlist.m3u8"
    if not playlist_path.exists():
        raise HTTPException(404, "Stream not found")
    return FileResponse(
        playlist_path,
        media_type="application/vnd.apple.mpegurl",
        headers={"Cache-Control": "no-cache, no-store"}
    )

@router.get("/{stream_id}/{segment_name}")
async def get_segment(stream_id: str, segment_name: str):
    """Serve HLS segment with byte-range support."""
    segment_path = STREAM_DIR / stream_id / segment_name
    if not segment_path.exists():
        raise HTTPException(404, "Segment not found")

    # Determine media type
    if segment_name.endswith(".ts"):
        media_type = "video/MP2T"
    elif segment_name.endswith(".m4s") or segment_name.endswith(".mp4"):
        media_type = "video/mp4"
    else:
        media_type = "application/octet-stream"

    return FileResponse(segment_path, media_type=media_type)
```

### 4.3 Async File Streaming for Large Segments

```python
async def stream_file(path: Path, chunk_size: int = 1024 * 1024):
    """Stream file in chunks using aiofiles."""
    async with aiofiles.open(path, 'rb') as f:
        while chunk := await f.read(chunk_size):
            yield chunk

@router.get("/{stream_id}/live.mp4")
async def get_fmp4_stream(stream_id: str):
    """Serve fMP4 live stream."""
    # This would connect to FFmpeg pipe output
    return StreamingResponse(
        stream_fmp4_from_encoder(stream_id),
        media_type="video/mp4"
    )
```

### 4.4 Registration in Main App

```python
# src/api/main.py
from src.api.streaming import router as streaming_router

app.include_router(streaming_router)
```

**Source**: [Streaming video with FastAPI](https://stribny.name/posts/fastapi-video/) - HIGH confidence
**Source**: [RTSP2HLS FastAPI Example](https://github.com/KamoliddinS/RTSP2HLS) - MEDIUM confidence

---

## 5. Content Types and CORS

### 5.1 Required MIME Types

| Resource | Content-Type | Notes |
|----------|--------------|-------|
| HLS Playlist | `application/vnd.apple.mpegurl` | Recommended per RFC |
| MPEG-TS Segment | `video/MP2T` | Standard TS type |
| fMP4 Segment | `video/mp4` | MP4 container |
| fMP4 Init | `video/mp4` | Initialization segment |
| DASH Manifest | `application/dash+xml` | If using DASH |

### 5.2 CORS Headers for Cast

Cast devices require CORS headers for adaptive streaming:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cast devices need this
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["Range", "Content-Type"],
    expose_headers=["Content-Length", "Content-Range", "Accept-Ranges"],
)
```

**Source**: [Google Cast Supported Media](https://developers.google.com/cast/docs/media) - HIGH confidence

### 5.3 Cache Headers for Live Streams

```python
# For playlists (should not be cached)
headers = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}

# For segments (can be cached)
headers = {
    "Cache-Control": "max-age=3600"  # 1 hour
}
```

---

## 6. Complete Requirements Update

### 6.1 Updated requirements.txt

```
# Existing v1.0 dependencies
playwright>=1.40.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pychromecast>=13.0.0
fastapi>=0.115.0
uvicorn>=0.32.0
structlog>=25.5.0

# New v1.1 streaming dependencies
m3u8>=6.0.0           # HLS playlist generation/parsing
aiofiles>=24.1.0      # Async file I/O for segment serving
```

### 6.2 Version Rationale

| Package | Version | Rationale |
|---------|---------|-----------|
| `m3u8>=6.0.0` | Latest stable (Aug 2024) | Mature, well-maintained, MIT license |
| `aiofiles>=24.1.0` | Latest stable | Async file I/O, Apache 2.0 license |

---

## 7. Alternative Approaches Considered

### 7.1 Separate aiohttp Server

**Pros**: Battle-tested for streaming, lower-level control
**Cons**: Adds complexity, requires port management, duplicates FastAPI functionality
**Decision**: NOT RECOMMENDED - FastAPI covers all requirements

### 7.2 ffmpeg-python Library

**Pros**: Pythonic FFmpeg interface
**Cons**: Abstracts away flags we need to control precisely
**Decision**: NOT RECOMMENDED - Direct subprocess with explicit flags preferred

### 7.3 python-hls Library

**Pros**: Dedicated HLS tooling
**Cons**: Less maintained than m3u8, FFmpeg handles segment generation
**Decision**: NOT RECOMMENDED - m3u8 + FFmpeg covers requirements

### 7.4 Nginx for Static Serving

**Pros**: Production-grade, high performance, X-Accel-Redirect support
**Cons**: Additional infrastructure, development overhead
**Decision**: CONSIDER FOR PRODUCTION - FastAPI sufficient for development

---

## 8. Sources Summary

### HIGH Confidence
- [globocom/m3u8 GitHub](https://github.com/globocom/m3u8) - Python HLS library
- [m3u8 on PyPI](https://pypi.org/project/m3u8/) - Package version info
- [FastAPI Custom Response Docs](https://fastapi.tiangolo.com/advanced/custom-response/) - Streaming support
- [OTTVerse HLS Packaging](https://ottverse.com/hls-packaging-using-ffmpeg-live-vod/) - FFmpeg HLS flags
- [FFmpeg Formats Documentation](https://ffmpeg.org/ffmpeg-formats.html) - Official FFmpeg docs
- [MDN Media Source Extensions](https://developer.mozilla.org/en-US/docs/Web/API/Media_Source_Extensions_API/Transcoding_assets_for_MSE) - fMP4 transcoding
- [Google Cast Supported Media](https://developers.google.com/cast/docs/media) - Cast requirements

### MEDIUM Confidence
- [FastAPI vs aiohttp](https://likegeeks.com/fastapi-vs-aiohttp/) - Framework comparison
- [Streaming video with FastAPI](https://stribny.name/posts/fastapi-video/) - Implementation patterns
- [RTSP2HLS GitHub](https://github.com/KamoliddinS/RTSP2HLS) - FastAPI HLS example
- [fMP4 Live Video Medium](https://medium.com/@vlad.pbr/in-browser-live-video-using-fragmented-mp4-3aedb600a07e) - fMP4 patterns
- [Unified Streaming fMP4 HLS](https://docs.unified-streaming.com/documentation/package/fmp4-hls.html) - CMAF flags
- [aiofiles GitHub Issue](https://github.com/aio-libs/aiohttp/issues/1404) - Async file serving

### LOW Confidence
- Performance characteristics (depend on deployment)
- Specific latency numbers (network-dependent)

---

*Research completed for Dashboard Cast Service v1.1 HTTP streaming stack*
