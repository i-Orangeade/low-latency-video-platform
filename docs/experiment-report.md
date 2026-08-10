# Experiment Report Draft

## Experiment Goals

Compare HTTP-FLV, WebRTC, and HLS under normal and weak-network conditions for drone inspection video transmission.

## Metrics

- End-to-end latency in milliseconds
- Average latency
- Maximum latency
- Frame rate
- Bitrate
- Stutter count
- Stream interruption count
- Recovery time after interruption

## Suggested Method

Use a test video with an embedded timestamp or a latency probe tool that records send and receive time. Run each protocol with the same input, resolution, frame rate, and encoding parameters.

Normal network experiments provide the baseline. Weak-network experiments use Linux `tc netem` to introduce delay, packet loss, or bandwidth limitation.

## Expected Thesis Discussion

HTTP-FLV is usually stable and easy to deploy, but latency is higher than WebRTC. WebRTC is suitable for low-latency monitoring, but deployment is more sensitive to network conditions and browser requirements. HLS has the highest latency but provides good compatibility and replay-oriented behavior.
