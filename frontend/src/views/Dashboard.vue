<script setup lang="ts">
import { onMounted, ref } from "vue";

import { type Alert, listAlerts } from "../api/alert";
import { type Device, listDevices } from "../api/device";

const devices = ref<Device[]>([]);
const alerts = ref<Alert[]>([]);

onMounted(async () => {
  devices.value = await listDevices().catch(() => []);
  alerts.value = await listAlerts().catch(() => []);
});
</script>

<template>
  <section>
    <h2 class="page-title">系统总览</h2>
    <div class="grid">
      <div class="card">
        <h3>设备数量</h3>
        <strong>{{ devices.length }}</strong>
      </div>
      <div class="card">
        <h3>未读告警</h3>
        <strong>{{ alerts.filter((item) => !item.is_read).length }}</strong>
      </div>
      <div class="card">
        <h3>主推流地址</h3>
        <p>rtmp://127.0.0.1/live/drone_001</p>
      </div>
    </div>
  </section>
</template>
