# Player Validation

This checklist validates the HTTP-FLV player behavior implemented in stages
6.1 through 6.5.

## Automated Check

Run from the repository root:

```bash
./scripts/validate_player.sh
```

The script checks the player event/reconnect contracts and runs the production
frontend build.

## Browser Acceptance

Rebuild the frontend container before testing a Docker deployment:

```bash
docker compose build frontend
docker compose up -d --no-deps frontend
```

Open the live page and hard refresh it:

```text
http://<ubuntu-host-ip>:5173/live
```

Use a temporary registered stream to avoid disturbing another test stream:

```bash
curl -X POST http://127.0.0.1:8000/api/video-sources \
  -H 'Content-Type: application/json' \
  -d '{"name":"Player validation","stream_id":"player_validation_001","enabled":true}'
```

Start the test source in another terminal:

```bash
STREAM_ID=player_validation_001 \
RTMP_URL=rtmp://127.0.0.1/live/player_validation_001 \
./deploy/ffmpeg/push_demo.sh
```

Select the temporary source in the live page. Verify that the video plays and
the browser Network panel requests:

```text
http://<ubuntu-host-ip>:8080/live/player_validation_001.live.flv
```

## Acceptance Cases

1. **Normal playback**
   - The video renders.
   - The browser Console has no repeated player errors.
   - The stream status API reports `online: true`.

2. **断流和自动重连**
   - Stop FFmpeg with `Ctrl+C`.
   - The player shows that playback was interrupted.
   - It attempts reconnects at roughly three-second intervals.
   - The Console shows the mpegts network error when the stream is unavailable.

3. **恢复推流**
   - Restart FFmpeg with the same `STREAM_ID` before the fifth attempt.
   - The player reconnects and resumes playback.
   - The next interruption starts again at reconnect attempt 1.

4. **达到重连上限**
   - Stop FFmpeg and leave it stopped for about 20 seconds.
   - The player stops retrying after five attempts.
   - The player shows a manual retry button.

5. **手动恢复**
   - Start FFmpeg again.
   - Click `手动重试`.
   - The player reconnects and clears the previous retry count.

6. **Switching sources**
   - Start a second test source.
   - Switch to it in the source selector.
   - The old player connection is released and only the new stream is requested.

7. **Cleanup**
   - Stop all test FFmpeg processes.
   - Delete temporary sources:

```bash
curl -X DELETE http://127.0.0.1:8000/api/video-sources/player_validation_001
```

The current implementation treats a `404` from ZLMediaKit as a missing live
media stream. That is expected while FFmpeg is stopped; it should trigger the
bounded reconnect flow rather than be treated as a frontend address failure.
