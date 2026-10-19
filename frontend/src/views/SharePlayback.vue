<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import VideoPlayer from "../components/VideoPlayer.vue";

const route = useRoute();

const mediaUrl = computed(() => {
  const value = route.query.url;
  if (typeof value !== "string" || !value.trim()) return "";

  try {
    const parsed = new URL(value, window.location.origin);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : "";
  } catch {
    return "";
  }
});
</script>

<template>
  <main class="share-playback">
    <VideoPlayer v-if="mediaUrl" :url="mediaUrl" />
    <div v-else class="share-playback__error" role="alert">
      播放地址无效
    </div>
  </main>
</template>

<style scoped>
.share-playback {
  min-height: 100vh;
  background: #05080f;
}

.share-playback :deep(.video-player) {
  height: 100vh;
  border-radius: 0;
}

.share-playback :deep(video) {
  height: 100vh;
  min-height: 0;
  object-fit: contain;
}

.share-playback__error {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  color: #fecaca;
  background: #05080f;
}
</style>
