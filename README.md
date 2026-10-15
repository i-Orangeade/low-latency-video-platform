# Low-Latency Live Video Platform

基础版低延迟实时视频平台：摄像头、编码器或 FFmpeg 测试源推送 RTMP，官方 ZLMediaKit 转 HTTP-FLV，Vue 播放，FastAPI 只管理视频源和流状态。

完整进阶能力（WebRTC、Hook、告警、录像、QoS、压测、自定义 ZLM）保存在 `advanced-archive` 分支，需要时从该分支迁回，而不是重新开发。

## 架构

```text
摄像头、编码器或测试源
  -> FFmpeg (H.264/AAC, RTMP)
  -> 官方 ZLMediaKit
       -> HTTP-FLV -> Vue (mpegts.js)
       -> getMediaList -> FastAPI -> SQLite 视频源表
浏览器 -> FastAPI（视频源 CRUD、播放地址、流状态）
```

视频不经过 FastAPI。媒体面由 ZLMediaKit 负责接流和分发，控制面只查询状态并登记视频源。

## 快速启动

要求 Docker Compose、FFmpeg 和 curl。

```bash
cp .env.example .env
```

把 `.env` 里的 `LLVP_ZLM_SECRET` 改成自己的密钥，然后启动三个服务：

```bash
./scripts/start_all.sh
```

### 管理员认证配置

当前版本提供单管理员登录、会话检查和退出接口。它只建立认证边界；视频源
CRUD 的权限保护将在下一阶段接入。项目不提供默认密码，未配置凭据时登录接口
返回 `503`。

在 `backend/` 中生成密码哈希，密码不会显示在终端，也不会写入命令历史：

```bash
cd backend
.venv/bin/python -m app.cli hash-admin-password
```

把输出写入本机 `.env`，不要提交真实值：

```env
LLVP_ADMIN_USERNAME=admin
LLVP_ADMIN_PASSWORD_HASH=scrypt:...
LLVP_AUTH_COOKIE_SECURE=false
```

重建后端使环境变量生效：

```bash
docker compose up -d --force-recreate --no-deps backend
```

认证 API 使用 `HttpOnly`、`SameSite=Strict` Cookie，并将会话保存在后端进程
内存中；后端重启后需要重新登录。当前局域网演示使用 HTTP，因此
`LLVP_AUTH_COOKIE_SECURE=false`。只有部署 HTTPS 后才能改为 `true`。

可以用 Cookie 文件验证认证流程：

```bash
curl -c /tmp/llvp-cookie -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}'

curl -b /tmp/llvp-cookie http://127.0.0.1:8000/api/auth/session
curl -b /tmp/llvp-cookie -X POST http://127.0.0.1:8000/api/auth/logout
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
`stream_id` 搜索，以及分页浏览。登记不是推流门禁，只是控制面管理。

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

任意客户端、摄像头或编码器都可以向 `rtmp://127.0.0.1/live/{stream_id}` 推流。`push_test_stream.sh` 会先登记 `stream_001`，再调用 FFmpeg 生成测试画面。也可以传入本地视频：

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

## 进阶版

```bash
git fetch origin
git checkout advanced-archive   # 完整进阶版
git checkout main               # 当前基础版
```
