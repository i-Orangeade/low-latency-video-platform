# drone-stream-platform

面向无人机巡检场景的低延迟视频传输与监控平台。

本项目不是飞控系统，也不是单纯播放器，而是围绕无人机巡检视频链路构建的 Web 监控平台：地面端通过 FFmpeg 或 C++ 工具推流到 ZLMediaKit，后端通过 ZLM HTTP API 和 Hook 管理流状态、录像、告警和实验数据，前端提供实时播放、状态监控和实验可视化。

## 技术栈

- 媒体核心：ZLMediaKit
- 推流与编码：FFmpeg
- 后端：Python FastAPI
- 前端：Vue 3 + Vite + TypeScript
- 数据库：SQLite
- 图表：ECharts
- 工具层：C++
- 部署：Linux + Docker

## 最小运行链路

第一阶段先跑通：

```text
测试视频或摄像头 -> FFmpeg -> RTMP -> ZLMediaKit -> HTTP-FLV -> 浏览器
```

启动 ZLMediaKit：

```bash
docker compose up -d zlm
```

推送测试流：

```bash
./scripts/push_test_stream.sh
```

HTTP-FLV 播放地址：

```text
http://127.0.0.1:8080/live/drone_001.live.flv
```

RTMP 推流地址：

```text
rtmp://127.0.0.1/live/drone_001
```

## 后端启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173
```

## 设计原则

ZLMediaKit 负责实时媒体接入、转协议和录制；FastAPI 负责业务状态、播放地址、告警和实验数据；Vue 负责监控展示；C++ 工具用于补充推流、延迟测量和状态采集能力。

这样划分可以把毕设主线聚焦在无人机视频传输平台，而不是从零实现媒体服务器。
