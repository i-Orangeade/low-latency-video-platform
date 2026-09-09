<script setup lang="ts">
import { onMounted, ref } from "vue";

import { getPlayUrl, getStreamStatus, type StreamStatus } from "../api/stream";
import StreamStatsPanel from "../components/StreamStatsPanel.vue";
import VideoPlayer from "../components/VideoPlayer.vue";

const streamId = ref("stream_001");
const playUrl = ref("");
const status = ref<StreamStatus | null>(null);

async function load() {
  const [play, currentStatus] = await Promise.all([
    getPlayUrl(streamId.value),
    getStreamStatus(streamId.value).catch(() => null)
  ]);
  playUrl.value = play.url;
  status.value = currentStatus;
}

onMounted(load);
</script>

<template>
  <section>
    <h2 class="page-title">实时监控</h2>
    <div class="card" style="margin-bottom: 16px">
      <div class="grid">
        <input v-model="streamId" class="input" placeholder="流 ID" />
        <button class="button" @click="load">刷新播放</button>
      </div>
      <p class="muted">播放地址：{{ playUrl }}</p>
    </div>
    <div class="grid" style="grid-template-columns: minmax(420px, 2fr) minmax(260px, 1fr)">
      <VideoPlayer :url="playUrl" />
      <StreamStatsPanel :status="status" />
    </div>
  </section>
</template>
