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

Set two different secrets:

- `LLVP_ZLM_SECRET` authenticates FastAPI calls to the ZLMediaKit HTTP API;
- `LLVP_ZLM_HOOK_SECRET` authenticates ZLMediaKit `on_publish` Hook calls.

Compose injects both values into the appropriate services. Never reuse one
secret for both purposes.

The backend stores control-plane data in SQLite. Alembic migrations run during
application startup, and can also be applied manually:

```bash
docker compose exec backend alembic upgrade head
```

## Start Services

```bash
./scripts/start_all.sh
```

This starts three containers: `llvp-zlm`, `llvp-backend`, and `llvp-frontend`.
ZLM uses a digest-pinned official image and only publishes RTMP `1935` and
HTTP `8080`.

## Register a Video Source and Push

```bash
./scripts/push_test_stream.sh
```

With a local file:

```bash
./scripts/push_test_stream.sh /path/to/demo.mp4
```

Registration is now a publish gate. Publishing an unknown or disabled
`stream_id` is rejected by ZLMediaKit after the FastAPI Hook returns failure.

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
GET /api/video-sources
GET /api/streams/stream_001/play-url
GET /api/streams/stream_001/status
POST /api/zlm/hooks/on_publish?token=<hook-secret>
```
