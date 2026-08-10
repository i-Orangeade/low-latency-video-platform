<script setup lang="ts">
import * as echarts from "echarts";
import { nextTick, onMounted, ref } from "vue";

import {
  createLatencyExperiment,
  type Experiment,
  listExperiments
} from "../api/experiment";

const chartRef = ref<HTMLDivElement | null>(null);
const experiments = ref<Experiment[]>([]);

async function refresh() {
  experiments.value = await listExperiments().catch(() => []);
  await nextTick();
  renderChart();
}

function renderChart() {
  if (!chartRef.value) {
    return;
  }
  const chart = echarts.init(chartRef.value);
  chart.setOption({
    title: { text: "协议端到端延迟对比" },
    tooltip: {},
    xAxis: { type: "category", data: experiments.value.map((item) => item.protocol) },
    yAxis: { type: "value", name: "延迟(ms)" },
    series: [
      {
        name: "平均延迟",
        type: "bar",
        data: experiments.value.map((item) => item.avg_latency_ms ?? 0)
      }
    ]
  });
}

async function seedDemoData() {
  await createLatencyExperiment({
    name: "HTTP-FLV baseline",
    stream_id: "drone_001",
    protocol: "flv",
    network_profile: "normal",
    encoder_params: "x264 veryfast zerolatency 720p25",
    avg_latency_ms: 850,
    max_latency_ms: 1300,
    bitrate_kbps: 1800,
    fps: 25,
    stutter_count: 1
  });
  await createLatencyExperiment({
    name: "WebRTC baseline",
    stream_id: "drone_001",
    protocol: "webrtc",
    network_profile: "normal",
    encoder_params: "x264 veryfast zerolatency 720p25",
    avg_latency_ms: 280,
    max_latency_ms: 520,
    bitrate_kbps: 1800,
    fps: 25,
    stutter_count: 0
  });
  await refresh();
}

onMounted(refresh);
</script>

<template>
  <section>
    <h2 class="page-title">性能实验</h2>
    <button class="button" style="margin-bottom: 16px" @click="seedDemoData">
      写入示例实验数据
    </button>
    <div class="card">
      <div ref="chartRef" style="height: 360px"></div>
    </div>
  </section>
</template>
