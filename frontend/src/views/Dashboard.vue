<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  type VideoSourceStatusSummary,
  getVideoSourceStatusSummary
} from "../api/videoSource";

const summary = ref<VideoSourceStatusSummary>({
  total: 0,
  online: 0,
  offline: 0,
  video_sources: []
});

onMounted(async () => {
  summary.value = await getVideoSourceStatusSummary().catch(() => summary.value);
});
</script>

<template>
  <section>
    <h2 class="page-title">系统总览</h2>
    <div class="grid">
      <div class="card">
        <h3>视频源数量</h3>
        <strong>{{ summary.total }}</strong>
      </div>
      <div class="card">
        <h3>在线视频源</h3>
        <strong>{{ summary.online }}</strong>
      </div>
      <div class="card">
        <h3>离线视频源</h3>
        <strong>{{ summary.offline }}</strong>
      </div>
      <div class="card">
        <h3>演示推流地址</h3>
        <p>rtmp://127.0.0.1/live/stream_001</p>
      </div>
      <div class="card">
        <h3>HTTP-FLV 播放</h3>
        <p>http://127.0.0.1:8080/live/stream_001.live.flv</p>
      </div>
    </div>
  </section>
</template>
