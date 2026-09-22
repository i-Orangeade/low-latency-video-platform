<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { getPlayUrl, getStreamStatus, type StreamStatus } from "../api/stream";
import { listVideoSources, type VideoSource } from "../api/videoSource";
import StreamStatsPanel from "../components/StreamStatsPanel.vue";
import VideoPlayer from "../components/VideoPlayer.vue";

const sources = ref<VideoSource[]>([]);
const selectedStreamId = ref("");
const playUrl = ref("");
const status = ref<StreamStatus | null>(null);
const isLoadingSources = ref(true);
const errorMessage = ref("");
let statusTimer: number | undefined;
const selectedSource = computed(() =>
  sources.value.find((source) => source.stream_id === selectedStreamId.value)
);

async function loadStatus() {
  if (!selectedStreamId.value) {
    status.value = null;
    return;
  }
  status.value = await getStreamStatus(selectedStreamId.value).catch(() => null);
}

async function load() {
  if (!selectedStreamId.value) {
    playUrl.value = "";
    status.value = null;
    return;
  }
  // 播放地址和在线状态互不依赖，并行请求可以减少切换视频源的等待时间。
  // 播放地址失败会直接抛出；状态查询失败则降级为 null，不影响播放器继续尝试连接。
  const [play, currentStatus] = await Promise.all([
    getPlayUrl(selectedStreamId.value),
    getStreamStatus(selectedStreamId.value).catch(() => null)
  ]);
  playUrl.value = play.url;
  status.value = currentStatus;
}

async function loadSources() {
  isLoadingSources.value = true;
  errorMessage.value = "";
  try {
    const response = await listVideoSources({ page: 1, pageSize: 100 });
    sources.value = response.items;
    if (!selectedStreamId.value && response.items.length > 0) {
      const defaultSource = response.items.find((source) => source.enabled) ?? response.items[0];
      selectedStreamId.value = defaultSource.stream_id;
      await load();
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "视频源加载失败";
  } finally {
    isLoadingSources.value = false;
  }
}

function startStatusPolling() {
  window.clearInterval(statusTimer);
  statusTimer = window.setInterval(() => void loadStatus(), 3000);
}

onMounted(async () => {
  await loadSources();
  startStatusPolling();
});

onBeforeUnmount(() => window.clearInterval(statusTimer));
</script>

<template>
  <section>
    <h2 class="page-title">实时监控</h2>
    <div class="card" style="margin-bottom: 16px">
      <div class="grid">
        <select v-model="selectedStreamId" class="select" :disabled="isLoadingSources" @change="load">
          <option value="" disabled>选择视频源</option>
          <option v-for="source in sources" :key="source.id" :value="source.stream_id">
            {{ source.name }}（{{ source.stream_id }}{{ source.enabled ? "，已启用" : "，已停用" }}）
          </option>
        </select>
        <button class="button" :disabled="!selectedStreamId" @click="load">刷新播放</button>
      </div>
      <div v-if="selectedSource && !selectedSource.enabled" class="notice notice--error" role="status">
        此视频源已停用；停用只改变管理状态，不会自动停止已经运行的 FFmpeg 推流。
      </div>
      <div v-if="errorMessage" class="notice notice--error" role="alert">{{ errorMessage }}</div>
      <div v-else-if="!isLoadingSources && sources.length === 0" class="notice notice--error" role="status">
        暂无已登记视频源，请先在视频源管理中创建。
      </div>
      <p class="muted">播放地址：{{ playUrl }}</p>
    </div>
    <div class="grid" style="grid-template-columns: minmax(420px, 2fr) minmax(260px, 1fr)">
      <VideoPlayer :url="playUrl" />
      <StreamStatsPanel :status="status" :enabled="selectedSource?.enabled" />
    </div>
  </section>
</template>
