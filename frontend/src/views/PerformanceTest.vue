<script setup lang="ts">
import * as echarts from "echarts";
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";

import {
  type Experiment,
  listExperiments
} from "../api/experiment";

const chartRef = ref<HTMLDivElement | null>(null);
const experiments = ref<Experiment[]>([]);
let chart: echarts.ECharts | null = null;

async function refresh() {
  experiments.value = await listExperiments().catch(() => []);
  await nextTick();
  renderChart();
}

function renderChart() {
  if (!chartRef.value) {
    return;
  }
  chart ??= echarts.init(chartRef.value);
  chart.setOption({
    title: { text: "真实端到端延迟样本" },
    tooltip: { trigger: "axis" },
    legend: { data: ["P50", "P95", "P99"] },
    xAxis: {
      type: "category",
      data: experiments.value.map((item) => `${item.protocol}/${item.network_profile}`)
    },
    yAxis: { type: "value", name: "延迟(ms)" },
    series: [
      {
        name: "P50",
        type: "bar",
        data: experiments.value.map((item) => item.p50_latency_ms ?? null)
      },
      {
        name: "P95",
        type: "bar",
        data: experiments.value.map((item) => item.p95_latency_ms ?? null)
      },
      {
        name: "P99",
        type: "bar",
        data: experiments.value.map((item) => item.p99_latency_ms ?? null)
      }
    ]
  }, true);
}

function handleResize() {
  chart?.resize();
}

onMounted(() => {
  void refresh();
  window.addEventListener("resize", handleResize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  chart?.dispose();
});
</script>

<template>
  <section>
    <h2 class="page-title">性能实验</h2>
    <p class="muted">
      仅展示由 latency_probe 上传的真实样本；测量边界和误差说明见 docs/latency-methodology.md。
    </p>
    <div class="card">
      <div ref="chartRef" style="height: 360px"></div>
    </div>
    <div class="card" style="margin-top: 16px; overflow-x: auto">
      <table>
        <thead>
          <tr>
            <th>实验</th>
            <th>流/协议</th>
            <th>网络</th>
            <th>样本</th>
            <th>P50</th>
            <th>P95</th>
            <th>P99</th>
            <th>方法</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in experiments" :key="item.id">
            <td>{{ item.name }}</td>
            <td>{{ item.stream_id }} / {{ item.protocol }}</td>
            <td>{{ item.network_profile }}</td>
            <td>{{ item.sample_count }}</td>
            <td>{{ item.p50_latency_ms?.toFixed(1) ?? "-" }} ms</td>
            <td>{{ item.p95_latency_ms?.toFixed(1) ?? "-" }} ms</td>
            <td>{{ item.p99_latency_ms?.toFixed(1) ?? "-" }} ms</td>
            <td>{{ item.measurement_method ?? "-" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
