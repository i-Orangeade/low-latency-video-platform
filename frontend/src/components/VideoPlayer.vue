<script setup lang="ts">
import mpegts from "mpegts.js";
import { onBeforeUnmount, ref, watch } from "vue";

const props = defineProps<{
  url: string;
  protocol: string;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
let player: mpegts.Player | null = null;

function destroyPlayer() {
  if (player) {
    player.destroy();
    player = null;
  }
}

function loadPlayer() {
  destroyPlayer();

  if (!videoRef.value || !props.url || props.protocol !== "flv") {
    return;
  }

  if (!mpegts.getFeatureList().mseLivePlayback) {
    return;
  }

  player = mpegts.createPlayer({
    type: "flv",
    isLive: true,
    url: props.url
  });
  player.attachMediaElement(videoRef.value);
  player.load();
  void videoRef.value.play().catch(() => undefined);
}

watch(() => [props.url, props.protocol], loadPlayer, { immediate: true });
onBeforeUnmount(destroyPlayer);
</script>

<template>
  <div class="video-player">
    <video ref="videoRef" controls muted playsinline />
    <div v-if="protocol !== 'flv'" class="protocol-note">
      当前协议 {{ protocol }} 已生成播放地址：{{ url }}
      <br />
      HTTP-FLV 已内置播放，WebRTC/HLS 后续可在此组件扩展对应播放器策略。
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
</style>
