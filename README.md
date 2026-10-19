# Low-Latency Live Video Platform

低延迟实时视频平台：摄像头、编码器或 FFmpeg 测试源推送 RTMP，ZLMediaKit
负责接流和 HTTP-FLV 分发，FastAPI 管理视频源、执行推流鉴权并查询流状态。
Vue 同时提供管理端实时监控和免登录分享播放页。

## 架构

```text
摄像头、编码器或测试源
  -> FFmpeg (H.264/AAC, RTMP)
  -> 官方 ZLMediaKit
       -> on_publish Hook -> FastAPI -> SQLite 视频源表
       -> HTTP-FLV -> Vue (mpegts.js)
浏览器 -> FastAPI（视频源 CRUD、播放地址、流状态）
```

视频不经过 FastAPI。媒体面由 ZLMediaKit 负责接流和分发；控制面负责视频源
登记、推流准入、播放地址和状态查询。

## 快速启动

要求 Docker Compose、FFmpeg、curl 和 OpenSSL。

```bash
cp .env.example .env
```

分别设置 ZLM API 密钥和独立的 Hook 密钥，然后启动三个服务：

```bash
openssl rand -hex 32
openssl rand -hex 32
```

把两个不同的随机值分别写入 `.env`：

```env
LLVP_ZLM_SECRET=...
LLVP_ZLM_HOOK_SECRET=...
```

`LLVP_ZLM_SECRET` 只用于 FastAPI 调用 ZLM API；`LLVP_ZLM_HOOK_SECRET`
只用于验证 ZLM 发出的推流 Hook。两者不能复用。

启动三个服务：

```bash
./scripts/start_all.sh
```

切换 Wi-Fi、手机热点或 VMware 桥接地址后，可自动同步前端使用的媒体地址：

```bash
./scripts/configure_public_host.sh
```

脚本读取默认路由网卡的 IPv4，更新本机 `.env` 中的
`LLVP_PUBLIC_ZLM_HOST`，确保服务已启动，并只重建后端容器。也可以显式指定
地址或网卡：

```bash
./scripts/configure_public_host.sh 192.168.4.174
NETWORK_INTERFACE=ens33 ./scripts/configure_public_host.sh
```

登记演示视频源并推测试流：

```bash
./scripts/push_test_stream.sh
```

默认地址：

- 前端：`http://127.0.0.1:5173`
- FastAPI 文档：`http://127.0.0.1:8000/docs`
- ZLM HTTP：`http://127.0.0.1:8080`
- RTMP 推流：`rtmp://127.0.0.1/live/stream_001`
- HTTP-FLV：`http://127.0.0.1:8080/live/stream_001.live.flv`

## 视频源管理

视频源控制面包含 `id`、`name`、`stream_id`、`enabled`、`created_at` 和
`updated_at`。前端「视频源管理」页面支持新增、编辑、删除、启停切换、按名称或
`stream_id` 搜索，以及分页浏览。只有已登记且启用的 `stream_id`
可以通过 RTMP 推流。

列表 API 支持以下查询参数：

```text
GET /api/video-sources?q=front&page=1&page_size=20&enabled=true
```

返回结果包含当前页 `items`、`total` 和 `total_pages` 等分页信息。也可以直接用 API
创建视频源：

```bash
curl -X POST http://127.0.0.1:8000/api/video-sources \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo source 001","stream_id":"stream_001"}'
```

## RTMP 推流

任意客户端、摄像头或编码器都可以向
`rtmp://127.0.0.1/live/{stream_id}` 发起推流，但 ZLMediaKit 会调用
FastAPI `on_publish` Hook。未登记或已停用的 `stream_id` 会被拒绝。

`push_test_stream.sh` 会先登记 `stream_001`，再调用 FFmpeg 生成测试画面。
也可以传入本地视频：

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

实时监控右侧会生成一个免登录分享地址，格式为：

```text
http://<frontend-host>:5173/play/share?url=<encoded-http-flv-url>
```

分享页只显示播放器，不包含视频源管理和实时监控导航。打开分享链接的观众
无需先进入管理界面；但媒体流本身仍需保持在线。

## 状态查询

后端调用官方 `getMediaList`，不缓存在线状态：

```text
GET /api/streams/stream_001/status
```

`online=true` 表示该 `stream_id` 当前有媒体。停推后应变为 `false`。

## 部署边界

当前版本定位为可信局域网演示环境，不包含管理端登录、推流账号或公网权限系统。
`on_publish` 只拒绝未登记和已停用的流，不替代用户身份认证。不要将 RTMP、
管理 API 或 ZLM HTTP 接口直接暴露到公网。

## 开发验证

后端：

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

数据库使用 SQLite 保存控制面数据，表结构由 Alembic migration 管理：

```bash
cd backend
.venv/bin/alembic upgrade head
```

应用启动时也会自动执行 `alembic upgrade head`。学习阶段如果本地数据不需要保留，可以删除 SQLite 文件后重新启动；后续新增字段或表必须新增 migration，不要只依赖 `create_all()`。

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

它会走：健康检查 → 登记视频源 → 推流 → `status.online=true` → 停流 → `status.online=false`。

## 范围说明

当前仓库聚焦 RTMP 接入、HTTP-FLV 播放、视频源管理、推流鉴权和播放器可靠性。
WebRTC、录像、告警、QoS、集群与公网生产部署不在当前版本范围内。
