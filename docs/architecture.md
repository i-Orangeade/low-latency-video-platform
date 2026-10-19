# Low-Latency Live Video Platform Architecture

## Goal

The platform ingests a live source from a camera, encoder, or FFmpeg test source
over RTMP, converts it to HTTP-FLV with a pinned official ZLMediaKit image, and
lets Vue players watch it through either the management live view or a standalone
share page. FastAPI registers video sources, authorizes publishers, and queries
stream status.

## Data Flow

```text
Camera, encoder, or FFmpeg test source
  -> RTMP
  -> Official ZLMediaKit
       -> on_publish Hook -> FastAPI -> SQLite video-source table
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

ZLMediaKit calls the authenticated `on_publish` Hook before accepting a
publisher. Only a registered, enabled stream ID with the expected app can publish.
The Hook uses a secret separate from the ZLM HTTP API secret.

The standalone `/play/share` frontend route displays only the player. It does not
render management navigation and only accepts HTTP or HTTPS media URLs.

## Learning Order

1. Start Compose and confirm `/api/health`.
2. Register `stream_001` and push RTMP with `scripts/push_test_stream.sh`.
3. Open the Vue live page and play HTTP-FLV.
4. Call `/api/streams/stream_001/status` while pushing and after stopping.
5. Read `deploy/zlm/config.template.ini` to see which protocols are enabled.
6. Read `backend/app/services/zlm_client.py` to see the ZLMediaKit HTTP API boundary.
7. Read `backend/app/services/stream_status_service.py` to see how ZLM media records
   become platform stream-status responses.

WebRTC, recording, alerting, QoS, clustering, and public production deployment
are outside the current scope.
