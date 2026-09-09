# drone-stream-platform

面向无人机巡检的低延迟视频监控与流媒体实验平台。项目将媒体面、控制面和展示面分离，
并维护一份固定版本的 ZLMediaKit 源码补丁，用真实采样数据验证流媒体链路。

## 核心能力

- FFmpeg 通过 RTMP 推送测试视频或摄像头画面。
- 自定义 ZLMediaKit 构建负责接流、HTTP-FLV/HLS/WebRTC 分发和录像。
- Vue 通过 mpegts.js 播放 HTTP-FLV，并实现 ZLM WebRTC SDP 协商。
- FastAPI 管理设备、流状态、录像、告警、实验结果和 ZLM Hook。
- `on_publish` 校验启用设备，所有 Hook 校验独立密钥。
- 流上下线状态同步、离线告警去重、MP4 Hook 幂等入库。
- C++ 延迟探针输出逐帧 CSV 和 P50/P95/P99，不再使用模拟延迟。
- 弱网、并发推流、QoS 查询和端到端 smoke test 脚本。

## 架构

```text
测试源/摄像头
  -> FFmpeg (H.264/AAC, RTMP)
  -> Custom ZLMediaKit
       -> HTTP-FLV / HLS / WebRTC -> Vue
       -> HTTP API / Hook         -> FastAPI -> SQLite
       -> getStreamQos            -> FastAPI -> 实时状态面板
```

视频数据不经过 FastAPI。后端只承担鉴权、状态、控制和数据持久化，避免业务服务成为
媒体带宽瓶颈。

## ZLMediaKit 源码改造

`zlm-custom/` 固定上游 commit
`da9b2017fbdd1738da4d68ff442b5eca3542c3ba`，构建时应用
`0001-add-stream-qos-api.patch`。

新增接口：

```text
GET /index/api/getStreamQos
```

接口在流所属 EventPoller 上复用 `MultiMediaSourceMuxer::addProbe` 进行有限时间采样，
返回 FPS、码率、关键帧数、平均 GOP、DTS 回退次数、采样首帧时间和读者数，不在永久
热路径上增加锁。详细设计见 `zlm-custom/README.md`。

## 快速启动

要求 Docker Compose、FFmpeg 和 curl。首次构建自定义 ZLM 会从源码编译，耗时较长。

```bash
cp .env.example .env
```

修改 `.env` 中两个密钥；从其他机器访问 WebRTC 时，将 `ZLM_RTC_EXTERN_IP` 设置为
宿主机可达 IP。然后启动完整平台：

```bash
./scripts/start_all.sh
```

推送测试流。脚本会先向后端注册 `drone_001`，以通过 `on_publish` 鉴权：

```bash
./scripts/push_test_stream.sh
```

默认地址：

- 前端：`http://127.0.0.1:5173`
- FastAPI 文档：`http://127.0.0.1:8000/docs`
- ZLM HTTP：`http://127.0.0.1:8080`
- RTMP 推流：`rtmp://127.0.0.1/live/drone_001`
- HTTP-FLV：`http://127.0.0.1:8080/live/drone_001.live.flv`

由于发布鉴权依赖后端，不应只启动 `zlm` 后再直接推流。

## 查询自定义 QoS

```bash
set -a
source .env
set +a
./scripts/query_stream_qos.sh drone_001 3000
```

平台后端也提供：

```text
GET /api/streams/drone_001/qos?probe_ms=3000
```

## 真实延迟实验

推流脚本会生成同机时钟 sidecar。另一个终端运行：

```bash
BACKEND_URL=http://127.0.0.1:8000 \
PROTOCOL=flv \
NETWORK_PROFILE=normal \
scripts/run_latency_experiment.sh \
  http://127.0.0.1:8080/live/drone_001.live.flv \
  /tmp/drone_001.latency-source \
  latency.csv
```

工具将逐帧数据写入 CSV，并把 P50/P95/P99 上传到性能实验页面。该指标的源端边界是
帧进入 FFmpeg `setpts` 滤镜的时刻，不包含摄像头曝光和显示器扫描，因此不虚称为严格
玻璃到玻璃延迟。误差模型见 `docs/latency-methodology.md`。

## 弱网与并发

```bash
scripts/mock_weak_network.sh apply --dev lo --rate 4mbit --delay 120 --loss 2
scripts/load_test_streams.sh --streams 20 --duration 300
scripts/mock_weak_network.sh clear --dev lo
```

请先阅读 `docs/benchmark.md`。在远程机器上错误操作物理网卡可能中断 SSH。

完整服务运行后可以执行：

```bash
set -a
source .env
set +a
scripts/integration_smoke_test.sh
scripts/recovery_smoke_test.sh
scripts/failure_recovery_test.sh
```

第一条验证设备注册、发布鉴权、推流上线、自定义 QoS、断流下线和离线告警；
第二条重启 FastAPI 与 ZLM 后重复该闭环；第三条在推流鉴权期间短暂停止 FastAPI，
验证 ZLM Hook 重试后能够继续发布。

已完成的 1/10/50/100 路结果、复现命令和限制见
`docs/benchmarks/2026-09-09.md`，可提交的原始汇总见
`docs/benchmarks/2026-09-09-summary.json`。

## 开发验证

后端：

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

前端：

```bash
cd frontend
npm ci
npm run build
npm audit --audit-level=high
```

C++ 与基础实验：

```bash
cmake -S cpp-tools -B cpp-tools/build
cmake --build cpp-tools/build -j
scripts/run_latency_experiment.sh --self-test

cmake -S labs -B labs/build
cmake --build labs/build -j
ctest --test-dir labs/build --output-on-failure
scripts/test_network_tools.sh
```

CI 配置位于 `.github/workflows/ci.yml`。

## 学习与面试材料

- `labs/README.md`：epoll、RAII、bounded queue、H.264/FLV 解析和调试工具。
- `docs/foundation-labs.md`：底层实验入口。
- `docs/career/`：简历表述、演示脚本、源码讲解和面试复盘模板。
- `docs/architecture.md`：平台职责边界。
- `docs/benchmark.md`：压测指标和实验方法。
- `docs/benchmarks/2026-09-09.md`：已执行的四档并发压测报告。

## 已知边界

- 严格玻璃到玻璃延迟仍需要画面时钟加外部相机/OCR或光电测量。
- HLS 浏览器播放目前依赖浏览器原生支持；Chrome 未引入 hls.js。
- SQLite 兼容迁移用于项目演示；正式生产部署应使用 Alembic 和外部数据库。
- TURN、公网 NAT、多节点调度和生产级监控仍需按实际部署环境完善。
