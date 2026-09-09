# Deploy

## Requirements

- Linux
- Docker and Docker Compose
- FFmpeg
- curl

## Environment

```bash
cp .env.example .env
```

Set `LLVP_ZLM_SECRET`. Compose injects this value into the official ZLMediaKit
config template and into FastAPI.

## Start Services

```bash
./scripts/start_all.sh
```

This starts three containers: `llvp-zlm`, `llvp-backend`, and `llvp-frontend`.
ZLM uses a digest-pinned official image and only publishes RTMP `1935` and
HTTP `8080`.

## Register a Device and Push

```bash
./scripts/push_test_stream.sh
```

With a local file:

```bash
./scripts/push_test_stream.sh /path/to/demo.mp4
```

## Play and Status URLs

HTTP-FLV:

```text
http://127.0.0.1:8080/live/stream_001.live.flv
```

RTMP ingest:

```text
rtmp://127.0.0.1/live/stream_001
```

Control plane:

```text
GET /api/health
GET /api/devices
GET /api/streams/stream_001/play-url
GET /api/streams/stream_001/status
```
