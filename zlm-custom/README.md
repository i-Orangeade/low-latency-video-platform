# Custom ZLMediaKit build

This directory turns the project's ZLMediaKit dependency into a reproducible
source-level customization instead of pulling the moving `master` image.

## Pinned upstream

- Repository: `https://github.com/ZLMediaKit/ZLMediaKit`
- Commit: `da9b2017fbdd1738da4d68ff442b5eca3542c3ba`
- Patch: `patches/0001-add-stream-qos-api.patch`

The Docker build fetches exactly that commit, verifies the patch with
`git apply --check`, applies it, and compiles MediaServer with WebRTC enabled.

## Added API

```text
GET /index/api/getStreamQos
```

Required query parameters:

- `secret`
- `vhost`
- `app`
- `stream`

Optional query parameter:

- `probe_ms`: sampling window in milliseconds, from 100 to 30000; default 1000

Example:

```bash
curl --get http://127.0.0.1:8080/index/api/getStreamQos \
  --data-urlencode "secret=${DRONE_STREAM_ZLM_SECRET}" \
  --data-urlencode "vhost=__defaultVhost__" \
  --data-urlencode "app=live" \
  --data-urlencode "stream=drone_001" \
  --data-urlencode "probe_ms=3000"
```

The response aggregates decoded-frame samples collected by ZLM's existing
`MultiMediaSourceMuxer::addProbe` path:

- sampled video/audio/frame counts and bytes
- sampled bitrate and video FPS
- keyframe count and average GOP duration
- DTS rollback count per track
- time until the first frame observed in the sampling window
- current readers, byte speed, and stream uptime

## Design and thread safety

The API schedules collection on the stream's owner `EventPoller`. It does not
install a permanent global frame callback and introduces no cross-thread lock
in the hot path. Collection lasts only for `probe_ms`, then aggregation runs
on the same owner poller.

`firstFrameDelayMs` is the delay from starting this sampling request until the
first frame arrives. It is not glass-to-glass latency. End-to-end latency is
measured separately by `cpp-tools/latency-probe`.

The endpoint can be disabled at runtime:

```ini
[api]
enableStreamQos=0
```

## Build

From the repository root:

```bash
docker compose build zlm
docker compose up -d
```

For a host-side source check against a ZLMediaKit checkout:

```bash
./zlm-custom/test_patch.sh /path/to/ZLMediaKit
```

After a host build, run a real RTMP functional test:

```bash
./zlm-custom/test_qos_runtime.sh \
  /path/to/ZLMediaKit/release/linux/Release/MediaServer
```

The test checks stream registration, validates sampled bitrate/FPS/timestamp
fields, stops the publisher, and verifies stream unregistration. A recorded
run and the NAL-versus-frame counting correction are documented in
`docs/qos-validation.md`.
