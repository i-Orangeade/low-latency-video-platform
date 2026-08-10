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

ZLMediaKit owns stream ingestion, protocol conversion, WebRTC signaling, HLS output, FLV output, RTSP output, and recording.

The frontend requests play URLs from FastAPI, then pulls media directly from ZLMediaKit. This avoids sending video traffic through the business backend.

## Protocol Choices

HTTP-FLV is used first because it is simple and stable for a minimum viable chain. WebRTC is added as the low-latency highlight after the basic monitoring platform works. HLS is kept for compatibility and playback of recorded or delayed content.

## Thesis Value

The project can support protocol latency comparison, weak-network experiments, stream quality monitoring, and alert rule design in a drone inspection scenario.
