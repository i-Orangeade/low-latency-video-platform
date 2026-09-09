# Low Latency Video Platform

基础版低延迟视频监控平台：FFmpeg 推 RTMP，官方 ZLMediaKit 转 HTTP-FLV，Vue 播放，FastAPI 只管理设备和流状态。

完整进阶能力（WebRTC、Hook、告警、录像、QoS、压测、自定义 ZLM）保存在 `advanced-archive` 分支，需要时从该分支迁回，而不是重新开发。

## 架构

```text
测试源或摄像头
  -> FFmpeg (H.264/AAC, RTMP)
  -> 官方 ZLMediaKit
       -> HTTP-FLV -> Vue (mpegts.js)
       -> getMediaList -> FastAPI -> SQLite 设备表
浏览器 -> FastAPI（设备 CRUD、播放地址、流状态）
```

视频不经过 FastAPI。媒体面由 ZLMediaKit 负责接流和分发，控制面只查询状态并登记设备。

## 快速启动

要求 Docker Compose、FFmpeg 和 curl。

```bash
cp .env.example .env
```

把 `.env` 里的 `LLVP_ZLM_SECRET` 改成自己的密钥，然后启动三个服务：

```bash
./scripts/start_all.sh
```

登记演示设备并推测试流：

```bash
./scripts/push_test_stream.sh
```

默认地址：

- 前端：`http://127.0.0.1:5173`
- FastAPI 文档：`http://127.0.0.1:8000/docs`
- ZLM HTTP：`http://127.0.0.1:8080`
- RTMP 推流：`rtmp://127.0.0.1/live/stream_001`
- HTTP-FLV：`http://127.0.0.1:8080/live/stream_001.live.flv`

## 设备登记

设备表只有 `id`、`name`、`stream_id`。登记不是推流门禁，只是演示管理。也可以用 API：

```bash
curl -X POST http://127.0.0.1:8000/api/devices \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo camera 001","stream_id":"stream_001"}'
```

## RTMP 推流

任意客户端都可以向 `rtmp://127.0.0.1/live/{stream_id}` 推流。`push_test_stream.sh` 会先登记 `stream_001`，再调用 FFmpeg 生成测试画面。也可以传入本地视频：

```bash
./scripts/push_test_stream.sh /path/to/demo.mp4
```

## HTTP-FLV 播放

打开前端「实时监控」，或直接访问：

```text
http://127.0.0.1:8080/live/stream_001.live.flv
```

后端固定返回 HTTP-FLV 地址：

```text
GET /api/streams/stream_001/play-url
```

## 状态查询

后端调用官方 `getMediaList`，不缓存在线状态：

```text
GET /api/streams/stream_001/status
```

`online=true` 表示该 `stream_id` 当前有媒体。停推后应变为 `false`。

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

全栈 smoke test（需已启动服务）：

```bash
./scripts/integration_smoke_test.sh
```

它会走：健康检查 → 登记设备 → 推流 → `status.online=true` → 停流 → `status.online=false`。

## 进阶版

```bash
git fetch origin
git checkout advanced-archive   # 完整进阶版
git checkout main               # 当前基础版
```
