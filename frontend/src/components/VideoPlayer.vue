<script setup lang="ts">
import mpegts from "mpegts.js";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{
  url: string;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
const errorMessage = ref("");
const isLoading = ref(false);
let player: mpegts.Player | null = null;
let loadGeneration = 0;

function releaseResources() {
  if (player) {
    player.destroy();
    player = null;
  }

  if (videoRef.value) {
    videoRef.value.pause();
    videoRef.value.removeAttribute("src");
    videoRef.value.srcObject = null;
    videoRef.value.load();
  }
}

function destroyPlayer() {
  loadGeneration += 1;
  releaseResources();
  isLoading.value = false;
}

async function playVideo(video: HTMLVideoElement) {
  try {
    await video.play();
  } catch {
    // The browser can still start playback through native controls.
  }
}

function loadFlv(video: HTMLVideoElement) {
  if (!mpegts.getFeatureList().mseLivePlayback) {
    throw new Error("当前浏览器不支持 HTTP-FLV 的 MSE 播放");
  }

  player = mpegts.createPlayer({
    type: "flv",
    isLive: true,
    url: props.url
  });
  player.attachMediaElement(video);
  player.load();
  void playVideo(video);
}

async function loadPlayer() {
  const generation = ++loadGeneration;
  releaseResources();
  errorMessage.value = "";
  isLoading.value = false;

  const video = videoRef.value;
  if (!video || !props.url) {
    return;
  }

  isLoading.value = true;
  try {
    loadFlv(video);
  } catch (error) {
    if (generation === loadGeneration) {
      errorMessage.value = error instanceof Error ? error.message : "播放器加载失败";
      releaseResources();
    }
  } finally {
    if (generation === loadGeneration) {
      isLoading.value = false;
    }
  }
}

watch(
  () => props.url,
  () => void loadPlayer()
);
onMounted(() => void loadPlayer());
onBeforeUnmount(destroyPlayer);
</script>

<template>
  <div class="video-player">
    <video ref="videoRef" controls muted playsinline />
    <div v-if="isLoading" class="protocol-note">正在连接 HTTP-FLV 播放流…</div>
    <div v-else-if="errorMessage" class="protocol-note error" role="alert">
      {{ errorMessage }}
    </div>
  </div>
</template>

<style scoped>
.video-player {
  overflow: hidden;
  border-radius: 14px;
  background: #0f172a;
}

video {
  display: block;
  width: 100%;
  min-height: 420px;
  background: #0f172a;
}

.protocol-note {
  padding: 14px;
  color: #e2e8f0;
  line-height: 1.7;
}

.protocol-note.error {
  color: #fecaca;
  background: rgb(127 29 29 / 35%);
}
</style>
