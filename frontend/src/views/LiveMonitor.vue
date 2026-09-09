<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  getPlayUrl,
  getStreamQos,
  getStreamStatus,
  startRecord,
  stopRecord,
  type StreamProtocol,
  type StreamQos,
  type StreamStatus
} from "../api/stream";
import StreamStatsPanel from "../components/StreamStatsPanel.vue";
import VideoPlayer from "../components/VideoPlayer.vue";
import { useStreamStore } from "../stores/stream";

const store = useStreamStore();
const streamId = ref(store.currentStreamId);
const protocol = ref<StreamProtocol>(store.currentProtocol);
const playUrl = ref("");
const status = ref<StreamStatus | null>(null);
const qos = ref<StreamQos | null>(null);
const message = ref("");

async function load() {
  store.setStream(streamId.value);
  store.setProtocol(protocol.value);
  const [play, currentStatus, currentQos] = await Promise.all([
    getPlayUrl(streamId.value, protocol.value),
    getStreamStatus(streamId.value).catch(() => null),
    getStreamQos(streamId.value, 1000).catch(() => null)
  ]);
  playUrl.value = play.url;
  status.value = currentStatus;
  qos.value = currentQos;
}

async function handleStartRecord() {
  await startRecord(streamId.value);
  message.value = "已向 ZLMediaKit 发送开始录像请求";
}

async function handleStopRecord() {
  await stopRecord(streamId.value);
  message.value = "已向 ZLMediaKit 发送停止录像请求";
}

onMounted(load);
</script>

<template>
  <section>
    <h2 class="page-title">实时监控</h2>
    <div class="card" style="margin-bottom: 16px">
      <div class="grid">
        <input v-model="streamId" class="input" placeholder="流 ID" />
        <select v-model="protocol" class="select">
          <option value="flv">HTTP-FLV</option>
          <option value="webrtc">WebRTC</option>
          <option value="hls">HLS</option>
          <option value="rtmp">RTMP</option>
          <option value="rtsp">RTSP</option>
        </select>
        <button class="button" @click="load">刷新播放</button>
      </div>
      <p class="muted">播放地址：{{ playUrl }}</p>
      <button class="button secondary" @click="handleStartRecord">开始录像</button>
      <button class="button secondary" style="margin-left: 8px" @click="handleStopRecord">
        停止录像
      </button>
      <span class="muted" style="margin-left: 12px">{{ message }}</span>
    </div>
    <div class="grid" style="grid-template-columns: minmax(420px, 2fr) minmax(260px, 1fr)">
      <VideoPlayer :url="playUrl" :protocol="protocol" />
      <StreamStatsPanel :status="status" :qos="qos" />
    </div>
  </section>
</template>
