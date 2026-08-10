# Deploy

## Requirements

- Linux
- Docker and Docker Compose
- FFmpeg
- Python 3.10+
- Node.js 18+

## Start ZLMediaKit

```bash
docker compose up -d zlm
```

Check container status:

```bash
docker compose ps
```

## Push a Test Stream

```bash
./scripts/push_test_stream.sh
```

With a local video file:

```bash
./scripts/push_test_stream.sh /path/to/demo.mp4
```

## Play URLs

HTTP-FLV:

```text
http://127.0.0.1:8080/live/drone_001.live.flv
```

HLS:

```text
http://127.0.0.1:8080/live/drone_001/hls.m3u8
```

RTSP:

```text
rtsp://127.0.0.1:8554/live/drone_001
```

RTMP:

```text
rtmp://127.0.0.1/live/drone_001
```

## Start Application Services

```bash
./scripts/start_all.sh
```

Use the `app` profile only after backend and frontend dependencies are ready.
