<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { createDevice, type Device, listDevices } from "../api/device";
import DeviceCard from "../components/DeviceCard.vue";

const devices = ref<Device[]>([]);
const form = reactive({
  // 默认值让首次打开页面时可以直接点击保存，快速体验完整流程。
  name: "Demo source 001",
  stream_id: "stream_001"
});

async function refresh() {
  devices.value = await listDevices().catch(() => []);
}

async function submit() {
  // 创建成功后重新拉取列表，页面始终以后端数据库返回的数据为准。
  await createDevice(form);
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
      <DeviceCard v-for="device in devices" :key="device.id" :device="device" />
    </div>
  </section>
</template>
