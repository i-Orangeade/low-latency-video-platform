# Architecture

## Goal

The platform receives real-time inspection video from a drone-side or ground-station-side encoder, distributes it through ZLMediaKit, and exposes monitoring, playback, recording, alerting, and experiment data through a Web system.

## Data Flow

```text
Drone or camera
  -> Ground station / encoder
  -> FFmpeg or C++ pusher
  -> RTMP/RTSP
  -> ZLMediaKit
  -> HTTP-FLV / WebRTC / HLS
  -> Browser
```

The backend does not forward media packets. It manages business data and calls ZLMediaKit APIs. This keeps the media plane and control plane separate.

## Control Plane

FastAPI owns devices, stream metadata, alert records, recording metadata, and experiment results.

The pinned custom ZLMediaKit build owns stream ingestion, protocol conversion,
WebRTC signaling, HLS/FLV/RTSP output, recording, and the windowed per-stream
QoS sampler. Its new API executes sampling on the stream owner poller and
returns aggregated metrics to FastAPI.

The frontend requests play URLs from FastAPI, then pulls media directly from ZLMediaKit. This avoids sending video traffic through the business backend.

## Startup and Failure Recovery

FastAPI starts first because its health endpoint and database initialization do
not require ZLM. ZLM waits for FastAPI to become healthy before starting, so
its `on_server_started` and subsequent authorization Hooks cannot race an
unready control plane. The frontend waits for FastAPI.

Both backend and ZLM use Compose restart policies and health checks.
`scripts/recovery_smoke_test.sh` restarts each service and then verifies device
registration, publish authorization, QoS, stream removal, and offline alerts.
`scripts/failure_recovery_test.sh` stops FastAPI during publish authorization;
ZLM retries Hook delivery up to five times at one-second intervals and the test
asserts that the stream registers after the control plane returns.
An active FFmpeg publisher does not reconnect automatically after a media
server restart; production senders must implement retry and backoff.

## Protocol Choices

HTTP-FLV remains the simple MSE baseline. WebRTC uses real SDP offer/answer
exchange with ZLM and RTC port 8001; public deployments must provide a
reachable ICE candidate address. HLS is kept for compatibility and native
browser playback where available.

## Thesis Value

The project supports source-PTS latency sampling, weak-network and concurrent
stream experiments, source-level ZLM QoS monitoring, and Hook-driven
authorization and alerting in a drone inspection scenario.
