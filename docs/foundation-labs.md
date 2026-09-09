# Foundation Track 实验说明

实现位于 `labs/`，独立于业务服务构建，目的是用可运行的小程序验证三个
基础能力：

1. Linux `epoll` echo server：RAII fd、非阻塞 accept/read/write、连接
   半关闭和按连接的发送缓冲区水位控制。
2. C++17 bounded queue：多生产者、多消费者、条件变量、关闭协议和结果
   完整性校验，可使用 ThreadSanitizer。
3. Python 媒体分析器：仅用标准库解析 Annex-B H.264 NAL 单元和完整 FLV
   tag header，输出机器可校验的 JSON 统计。

快速验收：

```bash
cmake -S labs -B labs/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build labs/build -j
ctest --test-dir labs/build --output-on-failure
```

完整的运行参数、输出字段、GDB、ASAN、TSAN、perf、tcpdump、ffprobe 和
Wireshark 命令见 [`labs/README.md`](../labs/README.md)。
