# v1.1 Cast Media Playback - Streaming Research

> Research Date: 2026-01-16
> Domain: HLS buffered streaming and fMP4 low-latency streaming for Google Cast devices

---

## Executive Summary

Google Cast devices support both HLS and fMP4 streaming with specific constraints:
- **Minimum segment duration**: 0.1 seconds (hard limit)
- **Recommended HLS segments**: 2-6 seconds for reliability, 6 seconds per Apple spec
- **Low-latency fMP4**: Can use CMAF chunks of 1-15 frames for sub-second latency
- **Codec baseline**: H.264 High Profile Level 4.1 minimum (all Cast devices)
- **Audio**: HE-AAC and LC-AAC universally supported

---

## 1. HLS Mode Specifications

### 1.1 Segment Duration

| Setting | Recommended | Range | Rationale |
|---------|-------------|-------|-----------|
| Target Duration | 4-6 seconds | 2-10s | Balance between latency and reliability |
| Minimum Segment | 0.1 seconds | Cast hard limit | Web Receiver Player requirement |
| GOP Size | Match segment | - | Keyframes at segment boundaries |
| Playlist Size | 3-5 segments | - | Standard live window |

**Source**: [Google Cast Streaming Protocols](https://developers.google.com/cast/docs/media/streaming_protocols) - HIGH confidence

**Key Behaviors**:
- Every `#EXT-X-TARGETDURATION` seconds, Cast reloads playlist/manifest
- For live streams, seeking allowed from beginning of newest list until 3 target durations from end
- Segments cut on next keyframe after target duration (FFmpeg behavior)

### 1.2 HLS Playlist Requirements

```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:6.000,
segment0.ts
#EXTINF:6.000,
segment1.ts
...
```

**Required Tags**:
- `#EXT-X-TARGETDURATION` - Maximum segment duration
- `#EXT-X-MEDIA-SEQUENCE` - Sequence number of first segment
- `#EXTINF` - Segment duration (must be followed by URI)

**Source**: [Google Cast Streaming Protocols](https://developers.google.com/cast/docs/media/streaming_protocols) - HIGH confidence

### 1.3 HLS Segment Formats

Cast supports multiple segment formats via `HlsSegmentFormat` and `HlsVideoSegmentFormat`:

| Format | Container | Use Case |
|--------|-----------|----------|
| TS | MPEG-2 Transport Stream | Default, most compatible |
| fMP4 | Fragmented MP4 | Requires Shaka player |
| AAC | Packed audio | Audio-only streams |
| AC3 | Dolby audio | Audio pass-through |

**Important**: Default Media Player Library (MPL) does NOT support HLS with fMP4 containers. Must use `useShakaForHls: true` for fMP4 HLS.

**Source**: [Bitmovin Community - HLS fMP4 on Chromecast](https://community.bitmovin.com/t/how-to-play-hls-streams-with-fmp4-container-in-chromecast-cafv3-receivers/2335) - MEDIUM confidence

### 1.4 Content Types for HLS

| MIME Type | Status | Notes |
|-----------|--------|-------|
| `application/vnd.apple.mpegurl` | Recommended | Per HLS RFC spec |
| `application/x-mpegURL` | Works | Legacy but functional |
| `video/m3u8` | Avoid | May not work on Cast |

**Source**: [pychromecast GitHub Issues](https://github.com/home-assistant-libs/pychromecast/issues/192) - MEDIUM confidence

---

## 2. fMP4 Mode Specifications (Low-Latency)

### 2.1 Fragment Duration

| Setting | Minimum | Recommended | Maximum |
|---------|---------|-------------|---------|
| Fragment Duration | 0.1s | 0.5-2s | 6s |
| CMAF Chunk Size | 1 frame | 1-15 frames | - |
| Keyframe Interval | 1s | 1-2s | 6s |

**Source**: [Google Cast Streaming Protocols](https://developers.google.com/cast/docs/media/streaming_protocols) - HIGH confidence (0.1s minimum)
**Source**: [Wowza Low-Latency CMAF](https://www.wowza.com/blog/low-latency-cmaf-chunked-transfer-encoding) - MEDIUM confidence (chunk sizing)

### 2.2 CMAF Low-Latency Architecture

```
Encoder -> [Chunk] -> [Chunk] -> [Chunk] = Fragment
           100ms     100ms      100ms     = 300ms fragment

Fragment -> Fragment -> Fragment = Segment (if needed)
```

**Key Insight**: With chunked-encoded CMAF, chunks are transferred immediately as encoded. This decouples latency from segment duration - same latency achievable with 10-second or 1-second segments.

**Source**: [Wowza CMAF Guide](https://www.wowza.com/blog/low-latency-cmaf-chunked-transfer-encoding) - MEDIUM confidence

### 2.3 fMP4 Initialization Segment

fMP4 requires an initialization segment containing:
- `ftyp` box (file type)
- `moov` box (movie metadata, codec info)

Followed by media segments containing:
- `moof` box (movie fragment header)
- `mdat` box (media data)

### 2.4 LL-HLS Buffer Defaults

For Low-Latency HLS:
- Default buffer: 3 part durations
- 400ms parts -> 1.2 second buffer
- Smaller parts = lower latency but more HTTP overhead

**Source**: [Dolby LL-HLS Optimization](https://optiview.dolby.com/resources/blog/streaming/how-to-optimize-ll-hls-for-low-latency-streaming/) - MEDIUM confidence

---

## 3. Cast Device Requirements and Limitations

### 3.1 Video Codec Support by Device

| Device | H.264 Profile | Max Resolution | Other Codecs |
|--------|---------------|----------------|--------------|
| Chromecast 1st/2nd Gen | High Profile Level 4.1 | 1080p/30fps, 720p/60fps | VP8 |
| Chromecast 3rd Gen | High Profile Level 4.2 | 1080p/60fps | VP8 |
| Chromecast Ultra | High Profile Level 5.1 | 4K/60fps | VP9, HEVC |
| Chromecast with Google TV | High Profile Level 5.2 | 4K/60fps | VP9, HEVC, AV1 |
| Google TV Streamer | High Profile Level 5.2 | 4K/60fps | VP9, HEVC, AV1 |
| Nest Hub / Hub Max | - | 720p/30-60fps | VP9 |

**Source**: [Google Cast Supported Media](https://developers.google.com/cast/docs/media) - HIGH confidence

### 3.2 Audio Codec Support

| Codec | Support | Notes |
|-------|---------|-------|
| LC-AAC | Universal | Recommended for compatibility |
| HE-AAC | Universal | Better compression |
| MP3 | Universal | Legacy support |
| Opus | Universal | Modern, efficient |
| Vorbis | Universal | WebM audio |
| FLAC | Universal | Up to 96kHz/24-bit |
| AC-3 (Dolby Digital) | Passthrough | Requires compatible TV |
| E-AC-3 (Dolby Digital Plus) | Passthrough | Requires compatible TV |

**Source**: [Google Cast Supported Media](https://developers.google.com/cast/docs/media) - HIGH confidence

### 3.3 Container Format Support

| Container | Video Codecs | Audio Codecs |
|-----------|--------------|--------------|
| MP4 | H.264, HEVC | AAC, MP3 |
| WebM | VP8, VP9 | Vorbis, Opus |
| MP2T (TS) | H.264 | AAC |
| OGG | - | Vorbis, Opus |

**Note**: HEVC is NOT compatible with Transport Stream containers on Cast.

**Source**: [Google Cast Supported Media](https://developers.google.com/cast/docs/media) - HIGH confidence

### 3.4 Hard Limitations

| Limitation | Value | Impact |
|------------|-------|--------|
| Minimum segment duration | 0.1 seconds | Cannot use sub-100ms segments |
| Image resolution cap | 1280x720 | Thumbnail/image limits |
| Live stream duration | -1 | Must set duration to -1 for live |
| CORS | Required | Must implement for adaptive streaming |

---

## 4. media_controller.play_media() API Details

### 4.1 Method Signature (pychromecast)

```python
def play_media(
    url: str,
    content_type: str,
    *,
    title: str | None = None,
    thumb: str | None = None,
    current_time: float | None = None,
    autoplay: bool = True,
    stream_type: str = STREAM_TYPE_LIVE,  # or STREAM_TYPE_BUFFERED
    metadata: dict | None = None,
    subtitles: str | None = None,
    subtitles_lang: str = "en-US",
    subtitles_mime: str = "text/vtt",
    subtitle_id: int = 1,
    enqueue: bool = False,
    media_info: dict | None = None,
    callback_function: CallbackType | None = None,
)
```

**Source**: [pychromecast media.py](https://github.com/home-assistant-libs/pychromecast/blob/master/pychromecast/controllers/media.py) - HIGH confidence

### 4.2 Key Parameters for Streaming

| Parameter | HLS Buffered | fMP4 Low-Latency | Notes |
|-----------|--------------|------------------|-------|
| `content_type` | `application/vnd.apple.mpegurl` | `video/mp4` | MIME type |
| `stream_type` | `STREAM_TYPE_BUFFERED` | `STREAM_TYPE_LIVE` | Affects seeking behavior |
| `current_time` | `0` or `None` | `None` (live edge) | Start position |
| `autoplay` | `True` | `True` | Start immediately |

### 4.3 Stream Types

```python
STREAM_TYPE_BUFFERED = "BUFFERED"  # VOD-like, full seeking
STREAM_TYPE_LIVE = "LIVE"          # Live, limited seeking
STREAM_TYPE_NONE = "NONE"          # Unknown/unspecified
```

**Important**: For live streams, set `stream_type="LIVE"` to enable proper live edge behavior.

### 4.4 Usage Example for Dual-Mode

```python
# HLS Buffered Mode
mc.play_media(
    url="http://server/stream.m3u8",
    content_type="application/vnd.apple.mpegurl",
    stream_type="BUFFERED",
    title="Dashboard Stream"
)

# fMP4 Low-Latency Mode
mc.play_media(
    url="http://server/stream.mp4",  # Or DASH manifest
    content_type="video/mp4",
    stream_type="LIVE",
    title="Camera Feed"
)
```

---

## 5. Real-World Implementation Patterns

### 5.1 Plex Chromecast Optimization

Plex uses these strategies for Cast streaming:
- **Transcoding**: Converts to Cast-native formats (MP4/H.264/AAC)
- **Quality**: Default 2 Mbps / 720p for 1st gen, higher for newer
- **Hardware acceleration**: Enabled for smoother playback
- **Auto quality**: Adjusts based on network conditions

**Source**: [Plex Support - Buffering](https://support.plex.tv/articles/201575036-why-is-my-video-stream-buffering/) - MEDIUM confidence

### 5.2 Live Streaming Latency Reality

Observed Cast behavior with live streams:
- Initial buffering: 20-60 seconds typical
- This is Cast behavior, not protocol limitation
- Workaround: Send "play" command after initial buffer fills

**Source**: [pychromecast Issue #356](https://github.com/home-assistant-libs/pychromecast/issues/356) - MEDIUM confidence

### 5.3 PlaybackConfig Buffer Settings

Custom Web Receivers can configure buffering via `PlaybackConfig`:

```javascript
const playbackConfig = new cast.framework.PlaybackConfig();
playbackConfig.autoResumeDuration = 5;  // Seconds of buffer before resume
playbackConfig.shakaConfig = {
  abr: {
    defaultBandwidthEstimate: 2000000  // 2 Mbps initial estimate
  }
};
```

**Source**: [Cast PlaybackConfig Reference](https://developers.google.com/cast/docs/reference/web_receiver/cast.framework.PlaybackConfig) - HIGH confidence

---

## 6. Recommended Configuration for v1.1

### 6.1 Buffered Mode (HLS) - Dashboard Reliability

```yaml
mode: buffered
segment_duration: 6  # seconds
playlist_size: 5     # segments in playlist
keyframe_interval: 6 # match segment duration
codec: h264
profile: high
level: 4.1           # universal Cast support
audio_codec: aac
audio_bitrate: 128k
video_bitrate: 2000k # safe for all devices
resolution: 1280x720 # universal support
content_type: application/vnd.apple.mpegurl
stream_type: BUFFERED
```

### 6.2 Low-Latency Mode (fMP4) - Camera Responsiveness

```yaml
mode: low_latency
fragment_duration: 0.5  # seconds (500ms)
keyframe_interval: 1    # every second
codec: h264
profile: high
level: 4.1
audio_codec: aac
audio_bitrate: 128k
video_bitrate: 2000k
resolution: 1280x720
content_type: video/mp4  # or application/dash+xml
stream_type: LIVE
```

### 6.3 FFmpeg Parameters

**HLS Buffered**:
```bash
ffmpeg -i input \
  -c:v libx264 -profile:v high -level 4.1 \
  -g 180 -keyint_min 180 \  # 6 sec at 30fps
  -c:a aac -b:a 128k \
  -f hls -hls_time 6 -hls_list_size 5 \
  -hls_flags delete_segments \
  output.m3u8
```

**fMP4 Low-Latency**:
```bash
ffmpeg -i input \
  -c:v libx264 -profile:v high -level 4.1 \
  -g 30 -keyint_min 30 \  # 1 sec at 30fps
  -c:a aac -b:a 128k \
  -f mp4 -movflags frag_keyframe+empty_moov+default_base_moof \
  -frag_duration 500000 \  # 500ms in microseconds
  output.mp4
```

---

## 7. Sources and Confidence Levels

### HIGH Confidence (Official Documentation)
- [Google Cast Supported Media](https://developers.google.com/cast/docs/media)
- [Google Cast Streaming Protocols](https://developers.google.com/cast/docs/media/streaming_protocols)
- [Cast PlaybackConfig Reference](https://developers.google.com/cast/docs/reference/web_receiver/cast.framework.PlaybackConfig)
- [Cast Live Streaming Guide](https://developers.google.com/cast/docs/web_receiver/live)
- [pychromecast Source Code](https://github.com/home-assistant-libs/pychromecast/blob/master/pychromecast/controllers/media.py)

### MEDIUM Confidence (Community/Third-Party)
- [Wowza Low-Latency CMAF](https://www.wowza.com/blog/low-latency-cmaf-chunked-transfer-encoding)
- [Dolby LL-HLS Optimization](https://optiview.dolby.com/resources/blog/streaming/how-to-optimize-ll-hls-for-low-latency-streaming/)
- [Bitmovin HLS fMP4 Discussion](https://community.bitmovin.com/t/how-to-play-hls-streams-with-fmp4-container-in-chromecast-cafv3-receivers/2335)
- [pychromecast GitHub Issues](https://github.com/home-assistant-libs/pychromecast/issues/356)
- [Plex Support Documentation](https://support.plex.tv/articles/201575036-why-is-my-video-stream-buffering/)

### LOW Confidence (General/Inferred)
- Specific latency numbers (vary by network/device)
- Buffer timing observations (device-dependent)

---

## 8. Open Questions for Implementation

1. **Custom Web Receiver**: Will we need a custom receiver for fMP4/CMAF low-latency, or can default media receiver handle it?
2. **DASH vs HLS for low-latency**: DASH may be better supported for fMP4 on Cast - needs testing
3. **Buffer tuning**: Default Cast buffering is aggressive (20-60s for live) - may need workarounds
4. **Codec detection**: Should use `canDisplayType()` to verify codec support before streaming

---

*Research completed for Dashboard Cast Service v1.1 dual-mode streaming implementation*
