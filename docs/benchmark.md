# 弱网与多路流压测

## 前置条件

主机需要 `iproute2`（提供 `tc`）和带 `libx264` 编码器的 FFmpeg。实际修改
qdisc 需要 root 权限；所有 `--dry-run` 命令都只打印操作，不调用 `sudo`、`tc`
或 `ffmpeg`。

在远程机器上操作物理网卡可能中断 SSH。建议先对 `lo`、容器专用 veth，或测试
命名空间验证。`lo` 上的规则会影响该主机全部回环流量。

## 弱网模拟

应用 4 Mbit/s 限速、120 ms 延迟和 2% 丢包：

```bash
scripts/mock_weak_network.sh apply \
  --dev lo --rate 4mbit --delay 120 --loss 2
```

脚本建立以下层级：

```text
HTB root (1:) -> HTB class (1:1) -> TBF (10:) -> netem (20:)
```

HTB 提供可挂载子队列的 classful 根，TBF 负责整形限速，netem 作为叶子队列注入
延迟和丢包。不要把 `netem` 直接设为根后再尝试挂载 TBF。

查看 qdisc、class 及累计丢包统计：

```bash
scripts/mock_weak_network.sh show --dev lo
tc -s qdisc show dev lo
tc -s class show dev lo
```

`apply` 完成后会检查 HTB `1:`、class `1:1`、TBF `10:` 和 netem `20:`
是否存在；任一缺失都会失败。清除规则：

```bash
scripts/mock_weak_network.sh clear --dev lo
```

执行前预览（无需 sudo，目标网卡可以不存在）：

```bash
scripts/mock_weak_network.sh apply --dev test0 --dry-run
scripts/mock_weak_network.sh show --dev test0 --dry-run
scripts/mock_weak_network.sh clear --dev test0 --dry-run
```

## 多路推流压测

启动 20 路、持续 300 秒的测试流：

```bash
scripts/load_test_streams.sh \
  --streams 20 \
  --duration 300 \
  --base-url rtmp://127.0.0.1/live \
  --prefix bench
```

流 ID 为 `bench_001` 到 `bench_020`。每一路由独立 FFmpeg 进程生成测试画面；
脚本收到 `INT` 或 `TERM` 时会终止并回收全部子进程。可通过 `--size`、`--fps`
和 `--bitrate` 固定输入负载，例如：

```bash
scripts/load_test_streams.sh -n 8 -d 120 \
  --size 1920x1080 --fps 25 --bitrate 2500k
```

仅检查将要执行的命令：

```bash
scripts/load_test_streams.sh -n 3 -d 10 --dry-run
```

测 ZLM 转发能力时，建议先生成预编码样本，再使用 `--input sample.flv` 令各进程
执行 codec copy；`--ramp-ms 100` 可避免把瞬时 Hook 连接风暴混入稳态容量结论。

## 指标采集

每次实验应记录机器型号、CPU 核数、内存、内核、FFmpeg/ZLMediaKit 版本、流数、
分辨率、帧率、码率、协议和弱网参数。至少预热 30 秒，再在固定时间窗内采样。
基线和弱网实验应使用相同输入与采样时长，并至少重复三轮。

### CPU

服务是宿主机进程时，先取得 PID，再以 1 秒间隔采样：

```bash
pidstat -u -p "$PID" 1 300 | tee cpu.log
```

记录平均 `%CPU` 和峰值。多核机器上进程 CPU 可能超过 100%，报告时应说明采用
“单核为 100%”还是除以逻辑核数后的整机百分比。容器部署可同时采集：

```bash
docker stats --no-stream
docker stats --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' | tee docker-stats.log
```

### RSS

使用 `pidstat` 采集 `RSS`（单位 KiB），避免只记录虚拟内存：

```bash
pidstat -r -p "$PID" 1 300 | tee rss.log
```

也可在固定时刻读取峰值高水位：

```bash
awk '/VmRSS|VmHWM/ {print}' "/proc/$PID/status"
```

报告稳定期平均 RSS、P95 RSS 和 `VmHWM`。容器指标应注明是容器 cgroup 使用量，
不能与单进程 RSS 混为一项。

### 吞吐

用网卡计数器测量入口和出口吞吐：

```bash
sar -n DEV 1 300 | tee network.log
```

`rxkB/s` 与 `txkB/s` 乘以 8 即为 kbit/s。使用回环网卡时，同一流量可能同时
出现在 RX 和 TX，不能把两者相加作为有效媒体吞吐。弱网实验同时保存
`tc -s qdisc show dev DEVICE`，其中 `Sent`、`dropped`、`overlimits` 和
`backlog` 可解释整形器是否饱和。

### 首帧时间

首字节时间不等于首个可解码视频帧。HTTP-FLV 可用 FFmpeg 解码第一帧，并用
墙钟计时：

```bash
/usr/bin/time -f '%e' -o first-frame.txt \
  timeout 30 ffmpeg -nostdin -loglevel error \
  -i http://127.0.0.1:8080/live/bench_001.live.flv \
  -frames:v 1 -f null -
```

输出单位为秒，包含建连、探测、缓冲和首帧解码。每次测量应新建播放器连接，
并确认命令成功退出；超时样本应单独报告，不能从统计中静默删除。若只测服务端
首字节，可使用 `curl -w '%{time_starttransfer}\n' -o /dev/null URL`，但必须
明确标注为 TTFB。

真正的玻璃到玻璃延迟需要在发送画面中叠加源端时钟，并在播放端截图/OCR 后与
同步时钟比较；它与上述“连接到首帧”指标不同。

### P95

将每次成功测得的首帧毫秒数或每秒 RSS 值每行一个写入 `samples.txt`。P95 使用
nearest-rank 定义，即排序后第 `ceil(0.95 * N)` 个样本：

```bash
sort -n samples.txt |
  awk '{v[NR]=$1} END {if (!NR) exit 1; i=int((NR*95+99)/100); print v[i]}'
```

报告样本数、成功数、超时/失败数、中位数和 P95。样本量过小时 P95 不稳定，
首帧测试建议至少 100 次独立连接。

## 自检

自检仅运行语法、参数校验与 dry-run，不修改系统网络：

```bash
scripts/test_network_tools.sh
```

## 1/10/50/100 路矩阵

完整服务启动后可运行自动化矩阵。每组先预热并等待目标唯一流数全部上线，再保存
Docker Engine stats、媒体列表快照、单流 QoS 和环境信息：

```bash
set -a
source .env
set +a

COUNTS="1 10 50 100" \
DURATION=120 \
WARMUP=15 \
RAMP_MS=100 \
scripts/run_benchmark_matrix.sh
```

结果写入 `benchmark-results/<UTC时间>/`，其中 `summary.json` 只做可复核的
CPU 均值/P95 与样本流 QoS 汇总；原始 JSON 和日志是最终依据。脚本不会自动声称
“无性能回退”，应在相同机器、相同输入下分别对未打补丁基线和当前构建运行，再比较
CPU、RSS、首帧、吞吐和失败率。

本仓库已执行一次短时四档矩阵，结果与边界见
[`docs/benchmarks/2026-09-09.md`](benchmarks/2026-09-09.md)。
