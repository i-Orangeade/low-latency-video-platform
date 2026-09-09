# 30 分钟源码深挖讲解结构

> 目标：让听众沿一条真实请求和一条真实媒体链路理解项目，而不是按目录念代码。标记规则：`[已落地]` 可由当前代码直接证明；`[部分落地]` 只有骨架或单侧实现；`[待验证]` 尚无完整实现或运行证据。

## 0:00—2:00 定义系统边界

核心图：

```text
测试源/摄像头
  -> FFmpeg 或 C++ 命令封装
  -> RTMP
  -> ZLMediaKit
  -> HTTP-FLV
  -> 浏览器

浏览器 -> FastAPI -> ZLM HTTP API
ZLM Hook -> FastAPI -> SQLite
```

讲解要点：

- `[已落地]` `README.md` 和 `docs/architecture.md` 定义媒体面/控制面分离。
- `[已落地]` 浏览器直接使用 ZLM 播放地址，FastAPI 不转发媒体包。
- `[已落地]` 仓库固定 ZLM commit，并以补丁形式维护 `getStreamQos` 源码扩展；其余协议栈、线程模型和缓存仍属于上游实现。

## 2:00—5:00 从进程编排进入

文件顺序：

1. `docker-compose.yml`
2. `scripts/start_all.sh`
3. `scripts/push_test_stream.sh`
4. `deploy/ffmpeg/push_demo.sh`

讲解：

- `[已落地]` Compose 编排 ZLM、FastAPI 和静态前端；FastAPI 先健康，再启动会立即发送 Hook 的 ZLM，前端同样等待后端。
- `[已落地]` ZLM 暴露 HTTP 8080、RTMP 1935、RTSP 8554、RTP 10000 TCP/UDP。
- `[已落地]` 推流脚本将测试源或文件经 FFmpeg 推到 `live/{stream_id}`。
- `[已落地]` Compose 映射 RTC 8001 TCP/UDP（与 FastAPI 8000 分离），并通过 `ZLM_RTC_EXTERN_IP` 配置 candidate 地址；公网 NAT 与浏览器路径仍需抓包验证。
- `[风险]` 活跃配置文件挂载为 `deploy/zlm/config.local.ini`，讲解配置时不能误指 `deploy/zlm/config.ini`。

## 5:00—9:00 跟一条播放请求

调用链：

1. `frontend/src/views/LiveMonitor.vue`
2. `frontend/src/api/stream.ts`
3. `backend/app/api/streams.py`
4. `backend/app/services/zlm_service.py`
5. ZLM `/index/api/getMediaList`
6. `frontend/src/components/VideoPlayer.vue`

讲解：

- `[已落地]` 页面保存流 ID 和协议，分别请求播放地址与状态。
- `[已落地]` 后端限制协议集合，并按公共主机/端口构造 FLV、HLS、WebRTC、RTMP、RTSP URL。
- `[已落地]` 状态查询调用 ZLM `getMediaList`，将空结果映射为 offline，将首条媒体记录映射为 schema、来源、观看人数和 tracks。
- `[已落地]` HTTP-FLV 由 `mpegts.js` 创建 live player，绑定 `<video>`，组件卸载或 URL 变化时销毁旧实例。
- `[已落地]` WebRTC 分支创建 recvonly transceiver、收集 ICE、向 ZLM POST offer SDP 并设置 answer；HLS 分支依赖浏览器原生 HLS。
- `[待验证]` 端口和信令代码已对齐，但公网 WebRTC 仍必须用 ICE candidate 与浏览器抓包证明，不能仅凭配置宣称打通。

建议现场问题：“如果 ZLM 不可用会怎样？”  
当前答案：状态接口捕获异常并返回 502；前端状态请求失败后置为 `null`。播放地址生成不探测媒体是否存在。

## 9:00—13:00 跟一条控制请求和一个 Hook

控制链：

- `LiveMonitor.vue` → `/start-record` 或 `/stop-record`
- `streams.py` → `zlm_service.start_record/stop_record`
- ZLM `startRecord/stopRecord`

Hook 链：

- `deploy/zlm/config.local.ini`
- `backend/app/api/zlm_hooks.py`
- `backend/app/services/alert_service.py` / `record_service.py`
- SQLAlchemy model → SQLite

讲解：

- `[已落地]` 录像控制透明转发 ZLM API 结果，错误映射为 502。
- `[已落地]` 所有 Hook 使用 Pydantic payload，并用 `hmac.compare_digest` 校验请求 URL token；payload secret/`admin_params` 仅作为兼容输入。
- `[已落地]` `on_publish` 检查流对应的设备存在且启用；活跃配置默认启用该 Hook，并在 Hook URL 查询参数中传递独立密钥。
- `[已落地]` 流注册/注销同步设备状态；恢复时解决未读离线告警，离线时复用同流未读告警。
- `[已落地]` MP4 完成时保存元数据，`file_path` 唯一约束与 `IntegrityError` 回查覆盖并发重复。
- `[部分落地]` `on_flow_report`、`on_server_started` 仅校验密钥后返回成功。
- `[待验证]` 离线告警是“先查再写”且无数据库唯一约束，现有测试只证明串行重复，不能证明并发幂等。

幂等改造的讲法：

1. 从上游字段确定事件身份，字段不足时定义可解释的复合键。
2. 数据库唯一约束作为并发兜底。
3. 业务记录与幂等键同事务。
4. 重复请求返回成功并记录重复计数。
5. 用串行重复、并发重复和“提交后响应丢失”测试验证。

注意：录像路径已落地数据库唯一约束；为离线告警设计事件键和并发唯一约束仍标记 `[待验证]`。

## 13:00—16:00 数据模型与页面

文件：

- `backend/app/models/device.py`
- `backend/app/models/alert.py`
- `backend/app/models/record.py`
- `backend/app/models/experiment.py`
- `backend/app/api/{devices,alerts,records,experiments}.py`
- `frontend/src/views/`

讲解：

- `[已落地]` 设备支持列表、新增、更新、删除，并检查 `stream_id` 重复。
- `[已落地]` 告警支持列表、测试告警和标记已读。
- `[已落地]` 录像当前是元数据查询，不是后端视频文件流服务。
- `[已落地]` 实验记录包含协议、网络配置、编码参数、平均/最大延迟、码率、FPS 和卡顿数。
- `[已落地]` 性能页已删除固定示例数据入口，只展示探针上传的样本数和 P50/P95/P99。
- `[部分落地]` Hook 已有 pytest 回归测试，但仓库仍没有迁移工具，也缺媒体端到端自动化。

## 16:00—19:00 C++ 工具现状

文件：

- `cpp-tools/stream-pusher/main.cpp`
- `cpp-tools/stream-health-agent/main.cpp`
- `cpp-tools/latency-probe/main.cpp`
- `cpp-tools/CMakeLists.txt`

逐个讲：

- `[已落地]` `stream_pusher` 拼装 FFmpeg 命令，可推测试图/正弦音或循环输入文件，使用 x264 `veryfast`、`zerolatency`、GOP 50、无 B 帧。
- `[已落地]` `stream_health_agent` 通过 `curl` 查询 FastAPI 状态接口。
- `[已落地]` `latency_probe` 解析 sidecar，以源起始 realtime 和帧 PTS 推导源端时刻，通过 fork/exec 安全启动 FFmpeg 解码真实播放 URL，并以 poll 读取逐帧 `showinfo`。
- `[已落地]` 探针输出逐帧 CSV 与 P50/P95/P99，脚本提供已知 10—50 ms 样本的离线 self-test。
- `[边界]` 测量不含摄像头曝光和显示扫描，sidecar 在 FFmpeg 启动前生成会引入固定正偏差；不是玻璃到玻璃。
- `[风险]` `stream_pusher` 与 `stream_health_agent` 仍依赖 `std::system`；延迟探针已避免 shell 展开并处理超时/子进程回收。

可追问：“为什么同时用 realtime 和 steady clock？”  
答：realtime 用于关联 sidecar 与接收时刻，steady clock 用于可靠超时；跨机不能直接相减，仍需 PTP/NTP 并单独统计时钟偏差。

## 19:00—22:00 弱网与实验方法

文件：

- `scripts/mock_weak_network.sh`
- `backend/app/models/experiment.py`
- `frontend/src/views/PerformanceTest.vue`
- `docs/experiment-report.md`

讲解：

- `[已落地]` 脚本校验参数，使用 HTB → TBF → netem 组合限速、延迟和丢包，并支持 dry-run、show、clear。
- `[已落地]` 非 dry-run apply 后会检查 qdisc/class 层级存在。
- `[已落地]` 多路 FFmpeg 推流脚本可固定并发流数、时长、分辨率、FPS 和码率，并回收子进程。
- `[已落地]` 网络工具自检覆盖 shell 语法、规则层级、参数传播和错误输入；延迟工具有离线计算自测。
- `[部分落地]` 数据模型与图表支持记录、展示实验。
- `[待验证]` 当前没有完整实验矩阵 runner，也没有可信容量或协议对比结果。
- `[待验证]` `docs/experiment-report.md` 中协议表现是预期讨论，不是本项目实测结论。

实验设计五个固定项：

1. 同一输入、编码参数、分辨率、帧率、GOP。
2. 写明网络拓扑和 `tc` 施加接口/方向。
3. 明确延迟起终点、时钟域和帧配对方式。
4. 预热、重复多轮，输出 P50/P95/P99、错误率与样本数。
5. 保存原始 CSV、环境版本和命令，图表可追溯到样本。

## 22:00—25:00 配置中的低延迟取舍

文件：`deploy/zlm/config.local.ini`

- `[已配置]` `modify_stamp=2`：使用源时间戳相对增量，并校正跳变/回退。
- `[已配置]` `mergeWriteMS=0`：关闭合并写缓存，倾向降低额外等待。
- `[已配置]` `continue_push_ms=15000`：推流短暂中断后允许续推。
- `[已配置]` HLS `segDur=2`、`segNum=3`。
- `[已配置]` RTC NACK 缓存、TWCC/REMB 相关参数使用配置默认或当前值。
- `[待验证]` 这些参数只有配置事实，没有 A/B 数据，不能直接推出延迟改善百分比。
- `[待验证]` `rtsp.directProxy=1` 与配置注释中的 WebRTC 兼容性提示需要结合实际接入协议验证。

## 25:00—27:30 线程、队列与 RingBuffer 深挖入口

当前应明确说：

- `[已落地]` `labs/src/epoll_echo_server.cpp` 实现单线程非阻塞 epoll、RAII fd、部分写处理和基于高水位的读背压。
- `[已落地]` `labs/src/bounded_queue_demo.cpp` 实现 mutex + condition_variable 的有界 MPMC 阻塞队列，支持关闭唤醒并校验生产/消费总量。
- `[已落地]` `labs/tests/run_tests.py` 覆盖队列、echo 大 payload 和 H.264/FLV 分析器；CMake 提供 ASAN/UBSAN 与 TSAN 选项。
- `[边界]` 有界阻塞队列不是媒体 RingBuffer，没有 GOP 边界、多读者游标或慢读者跳帧策略。
- `[已落地]` `zlm-custom/` 固定上游 commit，补丁从 `WebApi.cpp` 进入 `MediaSource::getOwnerPoller()`，再调用 `MultiMediaSourceMuxer::addProbe`；编译与真实 RTMP 流运行测试验证了调用链。
- `[边界]` QoS 补丁证明的是 owner poller 上的有限窗口采样，不代表已经掌握 ZLM 所有协议输出线程和 RingBuffer 慢读者策略。

后续源码深挖步骤：

1. 从已固定 commit 和可复现镜像出发，避免“看的是一版，跑的是另一版”。
2. 从 RTMP session 接收入口追到媒体源注册、帧分发和 HTTP-FLV/WebRTC 输出。
3. 为每个对象记录创建线程、回调线程、销毁线程和所有权。
4. 定位 RingBuffer 写入、读者订阅、GOP 缓存、慢读者策略。
5. 用 thread id 日志、断点和最小压测验证，而不是只凭类名推断。
6. 将已有 QoS 运行测试扩展为调用链图、关键类表、gdb 断点记录和多路性能对比。

## 27:30—29:00 压测分层

- `[已验证]` 输入面：1/10/50/100 路预编码 H.264 梯度接入；100 路 CPU 平均 198.90%、P95 217.34%、RSS P95 276.56 MiB，抽样流 25 FPS、DTS 回退为 0。
- `[已发现]` 控制面：瞬时百路接入会形成 Hook 连接风暴；采用状态驱动预热与 100 ms 梯度接入后稳定达到 100 路。SQLite 使用 WAL，但生产仍应引入外部数据库或事件队列。
- `[已验证]` 恢复：自动化脚本重启 FastAPI 与 ZLM 后重新执行发布鉴权、QoS、下线和告警闭环。
- `[待验证]` 播放与长稳：100 个 HTTP-FLV/WebRTC 播放端、小时级 RSS/FD/线程趋势和原版/修改版同机 A/B。
- `[待验证]` 工具选择前先定义负载；短请求工具不能代表长连接媒体容量。

当前能展示弱网/多路流 dry-run 与工具自检，不能展示已完成容量结果。

## 29:00—30:00 收束

建议总结：

“当前版本证明了基于固定 ZLM commit 的单流 QoS 源码扩展、FastAPI 控制面、带测试的 Hook、延迟采样、WebRTC 播放代码、弱网/多路流工具和 C++ 基础实验。QoS 补丁已经编译、运行并完成 1/10/50/100 路短时容量验证；下一阶段是公网 WebRTC、真实播放端与长期 A/B 稳定性。”

## 现场证据清单

- 启动：`./scripts/start_all.sh`
- 推流：`./scripts/push_test_stream.sh`
- 健康检查：`http://127.0.0.1:8000/api/health`
- HTTP-FLV：`http://127.0.0.1:8080/live/drone_001.live.flv`
- 状态：`http://127.0.0.1:8000/api/streams/drone_001/status`
- 弱网 dry-run：`./scripts/mock_weak_network.sh apply --dev lo --dry-run`
- 网络工具自检：`./scripts/test_network_tools.sh`
- 延迟计算自检：`./scripts/run_latency_experiment.sh --self-test`
- ZLM 补丁：`./zlm-custom/test_patch.sh /path/to/ZLMediaKit`
- ZLM QoS 运行测试：`./zlm-custom/test_qos_runtime.sh /path/to/MediaServer`
- 四档压测：`./scripts/run_benchmark_matrix.sh` 与 `docs/benchmarks/2026-09-09.md`
- 重启恢复：`./scripts/recovery_smoke_test.sh`
- C++ 构建：`cmake -S cpp-tools -B cpp-tools/build && cmake --build cpp-tools/build`
- 基础实验：`cmake -S labs -B labs/build && cmake --build labs/build && ctest --test-dir labs/build`

若任一命令未在演示环境复跑，现场说“代码路径已具备、运行环境待验证”，不要把静态阅读当成运行结果。
