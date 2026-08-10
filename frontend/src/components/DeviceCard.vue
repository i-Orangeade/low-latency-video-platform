<script setup lang="ts">
import type { Device } from "../api/device";

defineProps<{
  device: Device;
}>();
</script>

<template>
  <div class="card">
    <h3>{{ device.name }}</h3>
    <p>流 ID：{{ device.stream_id }}</p>
    <p>位置：{{ device.location || "未设置" }}</p>
    <p :class="device.enabled ? 'status-online' : 'status-offline'">
      {{ device.enabled ? "启用" : "停用" }}
    </p>
  </div>
</template>
