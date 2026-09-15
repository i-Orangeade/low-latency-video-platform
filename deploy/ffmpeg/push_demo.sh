#!/usr/bin/env bash
set -euo pipefail

STREAM_ID="${STREAM_ID:-stream_001}"
RTMP_URL="${RTMP_URL:-rtmp://127.0.0.1/live/${STREAM_ID}}"
INPUT="${1:-}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required. Install it with: sudo apt install ffmpeg"
  exit 1
fi

if [[ -n "${INPUT}" ]]; then
  # 传入视频文件时循环推流，尽量模拟持续直播输入。
  # 编码参数说明：
  # - zerolatency：关闭编码器内部延迟等待；
  # - -g 50：25fps 下每 2 秒一个关键帧；
  # - -bf 0：关闭 B 帧，避免编码重排序增加等待；
  # - -f flv：使用 RTMP 常用 FLV 封装。
  exec ffmpeg -re -stream_loop -1 -i "${INPUT}" \
    -c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 \
    -c:a aac -ar 44100 -b:a 96k \
    -f flv "${RTMP_URL}"
fi

# 不传输入文件时生成 720p 测试画面和 1kHz 音频，便于快速验证完整链路。
exec ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=25 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -c:v libx264 -preset veryfast -tune zerolatency -g 50 -bf 0 \
  -pix_fmt yuv420p \
  -c:a aac -ar 44100 -b:a 96k \
  -f flv "${RTMP_URL}"
