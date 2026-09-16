# Low-Latency Live Video Platform Architecture

## Goal

The base platform ingests a live source from a camera, encoder, or FFmpeg test
source over RTMP, converts it to HTTP-FLV with a pinned official ZLMediaKit
image, and lets a Vue player watch it. FastAPI only registers video sources and
queries stream status.

## Data Flow

```text
Camera, encoder, or FFmpeg test source
  -> RTMP
  -> Official ZLMediaKit
  -> HTTP-FLV
  -> Browser (mpegts.js)

Browser
  -> FastAPI video-source and stream APIs
  -> SQLite video-source table
  -> ZLMediaKit getMediaList
```

## Media Plane vs Control Plane

ZLMediaKit owns ingest, protocol conversion, and HTTP-FLV delivery. FastAPI
never forwards media packets. It stores `id/name/stream_id` video sources and asks
ZLMediaKit whether a stream is currently published.

Video-source registration is a demo catalog, not a publish gate. Any client may push
to `rtmp://host/live/{stream_id}`.

## Learning Order

1. Start Compose and confirm `/api/health`.
2. Register `stream_001` and push RTMP with `scripts/push_test_stream.sh`.
3. Open the Vue live page and play HTTP-FLV.
4. Call `/api/streams/stream_001/status` while pushing and after stopping.
5. Read `deploy/zlm/config.template.ini` to see which protocols are enabled.
6. Read `backend/app/services/zlm_client.py` to see the ZLMediaKit HTTP API boundary.
7. Read `backend/app/services/stream_status_service.py` to see how ZLM media records
   become platform stream-status responses.

Advanced work (WebRTC, Hook, recording, QoS, benchmarks) lives on
`advanced-archive` and should be moved back item by item.
