# 演示与项目讲解脚本

## 演示前检查

1. 执行 `./scripts/start_all.sh`，确认 ZLM、后端、前端容器启动。
2. 打开 `http://127.0.0.1:8000/api/health` 与 `http://127.0.0.1:5173`。
3. 执行 `./scripts/push_test_stream.sh`，确认 `drone_001` 正在推流。
4. 预先验证 HTTP-FLV 可播放、状态接口可返回、录像按钮不会报错；WebRTC 只有在 RTC 端口与 ICE 路径已实测时才现场演示。
5. 性能页只展示探针上传的真实数据；没有原始 CSV 的数字不进入演示结论。
6. 若网络或浏览器不稳定，准备一段本机录屏；录屏必须标注“预录演示”。

## 3 分钟演示

### 0:00—0:25 场景与边界

话术：

“这是一个面向无人机巡检视频链路的 Web 监控平台。它不做飞控，也不从零实现媒体服务器。ZLMediaKit 处理实时媒体，FastAPI 处理控制面和业务数据，Vue 页面直接从 ZLM 拉流。”

屏幕：展示 `README.md` 的最小链路或口头描述：

`测试源 → FFmpeg → RTMP → ZLMediaKit → HTTP-FLV → 浏览器`

### 0:25—1:20 实时链路

操作：

1. 展示推流终端，指出流 ID 为 `drone_001`。
2. 打开“实时监控”，选择 HTTP-FLV，点击“刷新播放”。
3. 指出右侧状态中的在线状态、观看人数、Track 信息。

话术：

“前端向 FastAPI 请求播放地址和状态，但视频数据不经过 FastAPI，而是由浏览器直连 ZLM。这样把媒体面与控制面分开，避免 Python 后端成为视频转发瓶颈。播放器代码已覆盖 HTTP-FLV、WebRTC SDP/ICE 和浏览器原生 HLS，Compose 映射 RTC 8001 TCP/UDP；公网 ICE/NAT 仍需按目标环境实测。”

### 1:20—2:10 录像、Hook 与告警

操作：

1. 点击“开始录像”和“停止录像”，说明这是调用 ZLM HTTP API。
2. 如环境能生成 MP4，展示录像列表；否则只展示接口和代码，不声称已产生录像文件。
3. 停止推流后刷新告警页，展示离线告警；若 Hook 环境未生效，展示 `backend/app/api/zlm_hooks.py` 并说明待联调。

话术：

“ZLM 的流注销 Hook 会同步设备状态并去重未读离线告警，MP4 完成 Hook 以唯一文件路径去重录像元数据；所有 Hook 使用常量时间比较校验密钥，发布 Hook 还检查设备白名单。录像去重有数据库唯一约束，离线告警仍缺少并发唯一约束，所以不能泛化成完全幂等。”

### 2:10—2:45 弱网实验能力

操作：

```bash
./scripts/mock_weak_network.sh apply --dev lo --rate 4mbit --delay 120 --loss 2 --dry-run
```

话术：

“脚本能生成限带宽、时延和丢包的 `tc` 规则，另有多路 FFmpeg 推流工具。C++ 探针用 sidecar 和帧 PTS 计算同机源播放时间线到解码帧记录的延迟，输出 CSV 和分位数并上传页面；只有保存原始 CSV 的实验才进入结论。”

补充展示 `docs/benchmarks/2026-09-09.md`：说明 100 路采用预编码 H.264、100 ms 梯度接入，ZLM 平均约使用两个逻辑核，抽样流保持 25 FPS、DTS 回退为 0；同时主动说明每档仅 7 个稳态样本。

### 2:45—3:00 收束

“目前可交付的是 HTTP-FLV 控制闭环、WebRTC 信令实现、带鉴权与幂等测试的 Hook、ZLM 单流 QoS 源码扩展，以及 1/10/50/100 路压测和服务重启恢复证据。尚未完成的是公网 NAT/TURN、长稳 A/B 和严格玻璃到玻璃测量。”

## 10 分钟项目讲解

### 0:00—1:00 问题定义

- 无人机巡检需要实时画面、状态、录像、告警和网络实验能力。
- 核心矛盾是低延迟、弱网稳定性、部署复杂度和可观测性的权衡。
- 项目目标是搭建可实验、可展示的平台，不把 ZLM 已有能力包装成自研媒体内核。

### 1:00—2:30 架构与数据流

- 推流：`scripts/push_test_stream.sh` 最终调用 FFmpeg，将测试源推到 `rtmp://127.0.0.1/live/drone_001`。
- 媒体面：ZLM 接入并转为 HTTP-FLV/HLS/RTSP/WebRTC 等协议。
- 控制面：`backend/app/services/zlm_service.py` 调用 ZLM API并生成播放地址。
- 展示面：`frontend/src/components/VideoPlayer.vue` 用 `mpegts.js` 播放 HTTP-FLV。
- 数据面边界：SQLite 保存设备、告警、录像元数据和实验记录，不保存实时视频帧。

可追问点：“为什么不让 FastAPI 代理视频？”  
答：这会增加一次拷贝和转发、放大连接与带宽压力，也模糊业务控制与媒体处理职责。

### 2:30—4:00 关键业务闭环

1. 前端请求 `/api/streams/{id}/play-url` 和 `/status`。
2. 后端通过 `getMediaList` 查询 ZLM 并规范化状态。
3. 录像按钮调用 `startRecord`/`stopRecord`。
4. `on_stream_changed` 在 `regist=false` 时创建离线告警。
5. `on_record_mp4` 在存在文件路径时保存录像元数据。

诚实边界：

- 设备 CRUD、告警列表/已读、录像列表、实验记录已存在。
- `on_publish` 已校验密钥并检查启用设备；`on_flow_report`、`on_server_started` 只做密钥校验后返回成功。
- 离线告警按“未读同类告警”应用层去重；录像按唯一文件路径去重并处理唯一冲突，二者保证级别不同。

### 4:00—5:20 播放协议选择

- HTTP-FLV：当前最小闭环，浏览器通过 MSE 和 `mpegts.js` 播放，部署直接。
- HLS：ZLM 配置为 2 秒目标分片、播放列表 3 片，通常以分片换兼容性，不应预设具体延迟。
- WebRTC：后端构造 ZLM 信令 URL，前端已实现 offer/answer、ICE 收集和远端 SDP；Compose 已映射 RTC 8001 TCP/UDP，公网 ICE/NAT 联调仍取决于部署环境。
- RTMP/RTSP：当前主要作为接入或工具协议，浏览器不能直接依赖原生播放。

### 5:20—6:40 时间戳与实验

- `Experiment` 表能保存协议、网络配置、编码参数、平均/最大延迟、码率、帧率和卡顿次数。
- `scripts/mock_weak_network.sh` 使用 HTB → TBF → netem 组合限带宽并注入时延、丢包。
- `deploy/ffmpeg/push_demo.sh` 生成同机 realtime 锚点和从零开始的 PTS，C++ 探针通过 `ffprobe` 读取真实播放 URL，输出 CSV 和 P50/P95/P99。
- 当前边界是“源播放时间线→ffprobe 帧记录”，包含进程启动偏差，不含摄像头曝光和显示扫描；跨机实验仍必须校时。

### 6:40—7:50 工程取舍

- Docker Compose 提供 ZLM、后端、前端编排，ZLM 日志和 SQLite 数据使用宿主机目录。
- FFmpeg 编码参数使用 `veryfast + zerolatency + GOP 50 + B 帧关闭`，目的是建立低延迟基线，而非证明最优。
- ZLM 活跃配置使用 `modify_stamp=2`、`mergeWriteMS=0`、`continue_push_ms=15000`；参数效果需要实验验证。
- FastAPI 使用异步 HTTP 客户端查询 ZLM，SQLAlchemy CRUD 仍是同步调用。

### 7:50—9:00 风险与下一步

按优先级讲：

1. 在公网或受控 NAT 环境验证 WebRTC ICE、TCP/TURN 回退路径。
2. 对真实 FLV/WebRTC URL重复运行延迟探针，补充跨机校时与外部画面时钟。
3. 为离线告警增加数据库级事件唯一约束和并发重试测试。
4. 在同一 commit 上执行原版与自定义 ZLM 长稳 A/B，加入真实播放端和首帧分布。
5. 将 SQLite 控制面迁移到 PostgreSQL 或事件队列，验证百路瞬时重连风暴。

### 9:00—10:00 总结与问答入口

总结：

“我完成了基于 ZLM 的媒体/控制面平台，并在固定源码版本上增加单流 QoS API。最强证据是可运行链路、Hook/恢复自动化和百路原始压测数据；边界是公网 WebRTC、长稳 A/B 与玻璃到玻璃测量仍待补齐。”

主动邀请追问：

- 想看架构：从 `zlm_service.py` 讲媒体面/控制面。
- 想看工程细节：从 `zlm_hooks.py` 讲幂等和失败处理。
- 想看 C++：从三个 `cpp-tools` 的现状讲为何下一步需要真实时间戳和队列。
- 想看性能：从弱网脚本讲实验变量、指标与误差控制。
