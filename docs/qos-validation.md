# ZLM QoS 扩展验证记录

## 验证对象

- ZLMediaKit commit：`da9b2017fbdd1738da4d68ff442b5eca3542c3ba`
- 补丁：`zlm-custom/patches/0001-add-stream-qos-api.patch`
- 日期：2026-09-09
- 主机：Linux 5.15.0-139-generic，x86_64，8 个逻辑 CPU
- 编译器：G++ 9.4.0
- 输入：FFmpeg `testsrc`，320×180，25 fps，x264 ultrafast/zerolatency，
  GOP 25，无 B 帧，RTMP

## 验证命令

源码先以 Release、`ENABLE_WEBRTC=OFF` 完整编译；该开关只用于缩短本机验证，
Dockerfile 的可交付构建仍启用 WebRTC。

```bash
./zlm-custom/test_patch.sh /path/to/ZLMediaKit
cmake -S /path/to/ZLMediaKit -B /path/to/ZLMediaKit/build \
  -DENABLE_WEBRTC=OFF -DENABLE_TESTS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build /path/to/ZLMediaKit/build -j2
./zlm-custom/test_qos_runtime.sh \
  /path/to/ZLMediaKit/release/linux/Release/MediaServer
```

运行测试会启动独立端口的 MediaServer，推送真实 RTMP 流，等待媒体源上线，调用
`getStreamQos`，停止推流，再确认媒体源注销。

## 原始响应

```json
{
  "aliveSecond": 1,
  "app": "live",
  "audioBytes": 2888,
  "audioFrameCount": 8,
  "averageGopMs": null,
  "bitrateKbps": 224.704,
  "configFrameCount": 2,
  "currentBytesSpeed": 37359,
  "firstFrameDelayMs": 4,
  "frameCount": 85,
  "keyFrameCount": 1,
  "probeMs": 1000,
  "readerCount": 0,
  "sampleBytes": 28088,
  "stream": "qos_runtime_test",
  "timestampRollbackCount": 0,
  "totalReaderCount": 0,
  "vhost": "__defaultVhost__",
  "videoBytes": 25200,
  "videoFps": 25.0,
  "videoFrameCount": 25
}
```

第一次实现直接把 H.264 NAL 单元数当作帧数，25 fps 输入被错误统计为 75 fps。
修正后按同一 track 的唯一 DTS 计数，运行结果恢复为 25 fps。这个过程说明“Frame”
对象不必然等于一幅视频画面，媒体统计必须先定义访问单元边界。

## 结论与边界

- 补丁能在固定 commit 上反向校验、完整编译并运行。
- 25 fps 输入在 1 秒采样窗内得到 25 个唯一视频 DTS。
- 码率、首帧、读者、关键帧和时间戳回退字段均能返回。
- 单秒窗口只有一个关键帧时，`averageGopMs=null` 是正确结果；至少两个关键帧才可
  计算 GOP 间隔。
- 该记录只证明功能正确性，不是 1/10/50/100 路性能结论。容量和性能回归必须用
  `scripts/run_benchmark_matrix.sh` 在同一目标机器上分别跑基线与补丁版本。
