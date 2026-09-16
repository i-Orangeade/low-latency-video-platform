<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { createVideoSource, type VideoSource, listVideoSources } from "../api/videoSource";
import VideoSourceCard from "../components/VideoSourceCard.vue";

const videoSources = ref<VideoSource[]>([]);
const form = reactive({
  name: "Demo source 001",
  stream_id: "stream_001"
});

async function refresh() {
  videoSources.value = await listVideoSources().catch(() => []);
}

async function submit() {
  await createVideoSource(form);
  await refresh();
}

onMounted(refresh);
</script>

<template>
  <section>
    <h2 class="page-title">视频源管理</h2>
    <div class="card" style="margin-bottom: 16px">
      <h3>新增视频源</h3>
      <div class="grid">
        <input v-model="form.name" class="input" placeholder="视频源名称" />
        <input v-model="form.stream_id" class="input" placeholder="流 ID" />
      </div>
      <button class="button" style="margin-top: 12px" @click="submit">保存视频源</button>
    </div>
    <div class="grid">
      <VideoSourceCard
        v-for="source in videoSources"
        :key="source.id"
        :source="source"
      />
    </div>
  </section>
</template>
