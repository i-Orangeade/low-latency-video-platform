<script setup lang="ts">
import { onMounted, ref } from "vue";

import { type Device, listDevices } from "../api/device";

const devices = ref<Device[]>([]);

onMounted(async () => {
  // 总览页只读取视频源数量；接口失败时降级为空列表。
  devices.value = await listDevices().catch(() => []);
});
</script>

<template>
  <section>
    <h2 class="page-title">系统总览</h2>
    <div class="grid">
      <div class="card">
        <h3>视频源数量</h3>
        <strong>{{ devices.length }}</strong>
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
