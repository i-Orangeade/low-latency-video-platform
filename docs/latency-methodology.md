# 直播延迟测量方法

## 测量的边界

本工具实现的是**同一台机器、同一 `CLOCK_REALTIME` 基准下的源端播放时间线到
探针收到帧时间戳的延迟**：

```text
capture_epoch(frame) = source_start_epoch + (frame_pts - pts_origin)
latency(frame) = probe_receive_epoch(frame) - capture_epoch(frame)
```

`push_demo.sh` 在启动 ffmpeg 前写出 source sidecar，并用 ffmpeg 的 `RTCTIME`
为每个视频帧生成相对该锚点的 PTS。因而这里的“采集时间”有明确的软件边界：
**源端视频帧进入 `setpts` 滤镜时的 wall-clock**，不是摄像头曝光时刻。`latency_probe`
通过参数数组直接启动系统 `ffmpeg`，从真实直播播放 URL 读取并解复用/解码视频帧，
用 `showinfo` 在每帧解码时即时报告 PTS，以该记录到达探针进程的 wall-clock 作为
接收时间。没有使用会批量缓冲帧输出的 `ffprobe -show_frames`。URL 不经过 shell
展开；以 `-` 开头的 URL 会被拒绝，避免被解释为 ffmpeg 选项。

这不是严格的玻璃到玻璃测量。它不包含摄像头曝光、传感器读出、显示器扫描与人眼所见
等环节；ffmpeg 的逐帧日志和进程管道也会带来少量观测开销。严格玻璃到玻璃需要在源画面中
显示可信 wall-clock/递增时间码，在接收显示画面上用相机拍摄并 OCR（或使用光电传感器）
后比较。本工具没有做 OCR，因此不会把结果标成玻璃到玻璃延迟。

## 已知误差

- sidecar 锚点在 ffmpeg 进程启动前生成，但每帧 PTS 来自处理该帧时的 `RTCTIME`，
  因此启动耗时不会被伪装成媒体延迟。纳秒锚点转换为 RTCTIME 的微秒单位会引入小于
  1 微秒的量化误差。
- 两端必须使用同机时钟。跨机器使用前必须以 PTP/NTP 校时并单独统计时钟偏差，否则结果
  不能归因于媒体链路。
- 播放协议或服务器可能重写/跳变 PTS。若 CSV 中延迟随时间明显线性漂移或突跳，应先检查
  PTS 连续性，不应直接报告分位数。
- 文件循环模式衡量的是文件实时播放调度，不是原视频拍摄时刻。长时间循环前应确认下游
  保留了单调 PTS。
- P50/P95/P99 使用排序样本上的线性插值分位数；负延迟通常表示 sidecar、URL 或时钟基准
  不匹配，应视为无效实验。

## 运行

先启动推流；sidecar 默认路径是 `/tmp/<STREAM_ID>.latency-source`：

```bash
STREAM_ID=drone_001 \
RTMP_URL=rtmp://127.0.0.1/live/drone_001 \
deploy/ffmpeg/push_demo.sh
```

另一个终端用**实际可播放 URL**运行探针（URL 取决于媒体服务器配置）：

```bash
scripts/run_latency_experiment.sh \
  http://127.0.0.1/live/drone_001.live.flv \
  /tmp/drone_001.latency-source \
  latency.csv
```

探针在标准输出打印 `samples`、`p50_ms`、`p95_ms`、`p99_ms`。逐帧 CSV 字段为：

- `frame`：探针样本序号；
- `pts_seconds`：ffmpeg 解码帧 `showinfo` 报告的 `pts_time`；
- `capture_epoch_ns`：由 sidecar 锚点和 PTS 推导的源端时间；
- `receive_epoch_ns`：探针收到该帧记录的 wall-clock；
- `latency_ms`：两者之差。

可用 `MAX_FRAMES` 和 `TIMEOUT_SECONDS` 调整采样：

```bash
MAX_FRAMES=1000 TIMEOUT_SECONDS=120 \
  scripts/run_latency_experiment.sh PLAYBACK_URL SOURCE_SIDECAR result.csv
```

## Self-test

离线 self-test 使用已知 PTS、接收时间和预期延迟（10/20/30/40/50 ms），验证 sidecar
解析、逐帧计算、CSV 和分位数，不需要媒体服务器：

```bash
scripts/run_latency_experiment.sh --self-test
```

该测试验证计算路径，不验证具体协议栈。完整实验仍应对部署中的真实播放 URL 运行。
