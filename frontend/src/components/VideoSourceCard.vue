<script setup lang="ts">
import type { VideoSource } from "../api/videoSource";

defineProps<{
  source: VideoSource;
}>();
</script>

<template>
  <div class="card">
    <h3>{{ source.name }}</h3>
    <p>流 ID：{{ source.stream_id }}</p>
  </div>
</template>
