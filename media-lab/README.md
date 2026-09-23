# FFmpeg Media Lab

This directory contains small, reproducible FFmpeg experiments used to understand
the media path of the Low-Latency Live Video Platform. The experiments are
intentionally separate from the application code: they explain how a test source
is generated, encoded, published, and played back.

The generated media files are local experiment artifacts. They are ignored by
Git, so this directory keeps the commands and observations without adding large
binary files to the repository.

## Scope

The lab covers four steps:

1. Generate a synthetic video and audio source.
2. Transcode a local file as a continuous live-like input.
3. Compare normal encoding with low-latency-oriented parameters.
4. Publish an FFmpeg source to ZLMediaKit over RTMP and verify HTTP-FLV playback.

The main project uses the same essential path:

```text
FFmpeg or camera
    -> RTMP
    -> ZLMediaKit
    -> HTTP-FLV
    -> frontend player
```

## Prerequisites

Install the tools on the Ubuntu host:

```bash
sudo apt install ffmpeg curl
ffmpeg -version
ffprobe -version
```

For the RTMP experiment, start the project services first:

```bash
cp .env.example .env
# Set LLVP_ZLM_SECRET in .env to the local ZLMediaKit API secret.
./scripts/start_all.sh
```

The examples below assume the commands are run from the repository root.

## Directory Layout

```text
media-lab/
├── 01-test-source/          # Synthetic test video and audio
├── 02-file-transcode/       # Local file used as a live-like input
├── 03-encoding-parameters/  # Normal and low-latency comparison
└── 04-rtmp-publish/         # RTMP publishing notes and checks
```

The output files mentioned below are intentionally not checked in:

```text
media-lab/**/*.mp4
```

## 1. Generate a Test Source

Generate a short MP4 containing an FFmpeg test pattern and a 1 kHz sine wave:

```bash
ffmpeg -y \
  -f lavfi -i testsrc=size=1280x720:rate=25 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -t 10 \
  -c:v libx264 -pix_fmt yuv420p \
  -c:a aac -ar 44100 -b:a 96k \
  media-lab/01-test-source/test-source.mp4
```

Inspect the generated streams:

```bash
ffprobe -v error \
  -show_entries stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate \
  -of table \
  media-lab/01-test-source/test-source.mp4
```

Expected observations:

- The file contains one H.264 video stream and one AAC audio stream.
- The video is 1280x720 at 25 frames per second.
- The audio sample rate is 44.1 kHz.
- `testsrc` makes frame continuity easy to recognize; the sine wave makes audio
  presence easy to verify.

## 2. Transcode a File as a Live-Like Input

Use the generated file as a continuous input. `-re` reads at the source frame
rate instead of processing as fast as possible, and `-stream_loop -1` repeats
the file:

```bash
ffmpeg -re -stream_loop -1 \
  -i media-lab/01-test-source/test-source.mp4 \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -g 50 -bf 0 \
  -c:a aac -ar 44100 -b:a 96k \
  -f mpegts \
  media-lab/02-file-transcode/output.ts
```

Stop the command with `Ctrl-C`. The important distinction is that this is a
continuous, paced input, rather than a batch conversion that finishes
immediately. The same input behavior is used by
`deploy/ffmpeg/push_demo.sh` when a local video file is supplied.

If an MP4 output is preferred for a short, finite conversion, use:

```bash
ffmpeg -y -i media-lab/01-test-source/test-source.mp4 \
  -c:v libx264 -c:a aac \
  media-lab/02-file-transcode/output.mp4
```

## 3. Compare Encoding Parameters

Create a normal-encoding sample:

```bash
ffmpeg -y \
  -f lavfi -i testsrc=size=1280x720:rate=25 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -t 10 \
  -c:v libx264 -preset medium \
  -c:a aac -ar 44100 -b:a 96k \
  media-lab/03-encoding-parameters/normal.mp4
```

Create a low-latency-oriented sample:

```bash
ffmpeg -y \
  -f lavfi -i testsrc=size=1280x720:rate=25 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -t 10 \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -g 50 -bf 0 -pix_fmt yuv420p \
  -c:a aac -ar 44100 -b:a 96k \
  media-lab/03-encoding-parameters/low-latency.mp4
```

Compare file size and stream metadata:

```bash
ls -lh media-lab/03-encoding-parameters/*.mp4
ffprobe -v error \
  -show_entries stream=codec_name,profile,has_b_frames,avg_frame_rate \
  -of table \
  media-lab/03-encoding-parameters/normal.mp4 \
  media-lab/03-encoding-parameters/low-latency.mp4
```

The low-latency command makes deliberate trade-offs:

- `-tune zerolatency` reduces encoder buffering.
- `-bf 0` disables B-frames, avoiding frame reordering delay.
- `-g 50` targets a keyframe every two seconds at 25 fps.
- `-preset veryfast` spends less time compressing each frame.

These settings are practical defaults for a learning project, not universal
production tuning. Resolution, frame rate, bitrate, network conditions, and
the decoder all affect the final latency.

## 4. Publish to ZLMediaKit over RTMP

The repository provides a wrapper that registers the source and starts a
synthetic FFmpeg stream:

```bash
STREAM_ID="media_lab_$(date +%Y%m%d_%H%M%S)" \
  ./scripts/push_test_stream.sh
```

For a local file input:

```bash
STREAM_ID="media_lab_file_$(date +%Y%m%d_%H%M%S)" \
  ./scripts/push_test_stream.sh \
  media-lab/01-test-source/test-source.mp4
```

The wrapper prints two useful addresses:

- RTMP ingest: normally `rtmp://127.0.0.1/live/{stream_id}` on the Ubuntu host.
- HTTP-FLV playback: built from `LLVP_PUBLIC_ZLM_HOST` and
  `LLVP_PUBLIC_ZLM_HTTP_PORT`.

When the browser runs on another machine, set the public host in `.env`, for
example:

```env
LLVP_PUBLIC_ZLM_HOST=192.168.8.128
LLVP_PUBLIC_ZLM_HTTP_PORT=8080
```

Then recreate the backend container if the environment was changed:

```bash
docker compose up -d --force-recreate backend
```

Verify the control plane and media plane separately:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/streams/<stream_id>/status
curl http://127.0.0.1:8000/api/streams/<stream_id>/play-url
```

The playback URL should return HTTP 200 while FFmpeg is publishing. Since
HTTP-FLV is a live response, `curl` may continue waiting after receiving bytes;
use a timeout for a bounded check:

```bash
curl --max-time 5 -o /tmp/media-lab.live.flv \
  -w 'HTTP status: %{http_code}\nDownloaded bytes: %{size_download}\n' \
  'http://127.0.0.1:8080/live/<stream_id>.live.flv'
```

Open the frontend at `http://127.0.0.1:5173/live` and select the registered
source. Stop FFmpeg with `Ctrl-C`, then confirm:

```bash
curl http://127.0.0.1:8000/api/streams/<stream_id>/status
```

The stream should eventually report `online: false`. If FFmpeg reports
`Already publishing`, another process is already using the same `stream_id`;
stop that process or choose a new ID.

## Conclusions

The experiments establish the minimum media knowledge needed for this project:

1. A playable stream needs compatible video and audio codecs, not just a
   container file.
2. A file must be paced with `-re` to behave like a live input.
3. Keyframe interval, B-frames, encoder buffering, and preset influence startup
   and end-to-end latency.
4. ZLMediaKit is the media-plane component; FastAPI manages source metadata and
   queries stream state.
5. The frontend should use the public playback address, while FFmpeg uses the
   host-local RTMP ingest address.

This is enough for the current undergraduate project scope. More advanced
topics such as WebRTC, adaptive bitrate, recording, QoS metrics, and horizontal
scaling belong in separate follow-up work.
