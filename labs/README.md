# Foundation Labs

这组实验仅依赖 Linux、C++17、CMake 和 Python 3，覆盖事件驱动网络、
线程同步与基础媒体封装分析。

## 构建和最小验收

```bash
cmake -S labs -B labs/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build labs/build -j
ctest --test-dir labs/build --output-on-failure
```

也可以直接执行测试入口：

```bash
python3 labs/tests/run_tests.py \
  --echo-server labs/build/epoll_echo_server \
  --queue-demo labs/build/bounded_queue_demo \
  --analyzer labs/tools/media_analyzer.py
```

测试会验证：多生产者/多消费者汇总不丢数据；echo server 在 32 KiB
高水位下完整回显 512 KiB 并正确处理半关闭；H.264/FLV 的正常样本统计
以及截断 FLV 的失败路径。

## epoll echo server

```bash
labs/build/epoll_echo_server 9000 262144
# 另一个终端：
printf 'hello\n' | nc 127.0.0.1 9000
```

服务端用 move-only RAII 对象管理 fd；监听和连接均为非阻塞模式；连接由
`epoll` 注册、更新、删除，并在映射移除时自动关闭。每个连接维护待发送
缓冲区：达到高水位时暂时取消 `EPOLLIN`，降到低水位后恢复读取，避免慢
接收端导致无界内存增长。`EPOLLRDHUP` 与读到 EOF 用于处理半关闭，剩余
回显数据发送完成后才释放连接。

GDB 与 ASAN：

```bash
gdb --args labs/build/epoll_echo_server 9000
# gdb 中：break EchoServer::service_connection，然后 run

cmake -S labs -B labs/build-asan \
  -DCMAKE_BUILD_TYPE=Debug -DFOUNDATION_ENABLE_ASAN=ON
cmake --build labs/build-asan -j
ASAN_OPTIONS=detect_leaks=1 \
  ctest --test-dir labs/build-asan --output-on-failure
```

网络抓包：

```bash
sudo tcpdump -i lo -nn -s0 -w /tmp/echo.pcap 'tcp port 9000'
# Wireshark 打开 /tmp/echo.pcap，显示过滤器：tcp.port == 9000
```

## bounded queue

参数依次是生产者数、消费者数、每个生产者的任务数和队列容量：

```bash
labs/build/bounded_queue_demo 4 3 100000 64
```

队列使用一个互斥量保护状态，`not_empty`/`not_full` 条件变量提供有界阻塞，
`close()` 唤醒所有等待线程。每个消费者只写自己的计数槽，主线程 join 后
汇总总数与序号和，因而可检测丢失或重复。

TSAN 验收：

```bash
cmake -S labs -B labs/build-tsan \
  -DCMAKE_BUILD_TYPE=Debug -DFOUNDATION_ENABLE_TSAN=ON
cmake --build labs/build-tsan -j
TSAN_OPTIONS=halt_on_error=1 \
  labs/build-tsan/bounded_queue_demo 4 4 20000 8
```

性能采样：

```bash
perf stat -e task-clock,context-switches,cycles,instructions \
  labs/build/bounded_queue_demo 4 4 1000000 64
perf record -g -- labs/build/epoll_echo_server 9000
# 产生负载后 Ctrl-C，再执行：
perf report
```

## H.264 / FLV 分析器

脚本自动识别 Annex-B H.264 和 FLV，也可用 `--format h264|flv` 明确指定。
输出为 JSON：H.264 包含 NAL 类型、偏移、字节数和 forbidden-zero-bit
错误数；FLV 包含 tag 类型、时间戳、payload 字节、PreviousTagSize 校验，
以及 AVC packet type 统计。结构截断或格式错误返回退出码 2。

```bash
python3 labs/tools/media_analyzer.py input.h264
python3 labs/tools/media_analyzer.py --compact input.flv | python3 -m json.tool
```

用 ffprobe 交叉验证：

```bash
ffprobe -v error -show_streams -show_packets -of json input.h264
ffprobe -v error -show_format -show_streams -show_packets -of json input.flv
```

抓取实际 FLV 后验收：

```bash
curl -o /tmp/live.flv 'http://127.0.0.1/live/drone_001.live.flv'
python3 labs/tools/media_analyzer.py /tmp/live.flv
ffprobe -v error -count_packets -show_streams /tmp/live.flv
```

Wireshark 可对承载 FLV 的 HTTP/TCP 流使用 `tcp.stream eq N`，然后选择
“Follow TCP Stream”；对 H.264/RTP 流可使用 `rtp` 或
`rtp.p_type == 96` 显示过滤器，再与脚本统计的 SPS/PPS/IDR 数量对照。
