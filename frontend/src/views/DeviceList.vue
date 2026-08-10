<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import { createDevice, type Device, listDevices } from "../api/device";
import DeviceCard from "../components/DeviceCard.vue";

const devices = ref<Device[]>([]);
const form = reactive({
  name: "巡检无人机 001",
  stream_id: "drone_001",
  location: "测试场地"
});

async function refresh() {
  devices.value = await listDevices().catch(() => []);
}

async function submit() {
  await createDevice(form);
  await refresh();
}

onMounted(refresh);
</script>

<template>
  <section>
    <h2 class="page-title">设备管理</h2>
    <div class="card" style="margin-bottom: 16px">
      <h3>新增设备</h3>
      <div class="grid">
        <input v-model="form.name" class="input" placeholder="设备名称" />
        <input v-model="form.stream_id" class="input" placeholder="流 ID" />
        <input v-model="form.location" class="input" placeholder="巡检位置" />
      </div>
      <button class="button" style="margin-top: 12px" @click="submit">保存设备</button>
    </div>
    <div class="grid">
      <DeviceCard v-for="device in devices" :key="device.id" :device="device" />
    </div>
  </section>
</template>
