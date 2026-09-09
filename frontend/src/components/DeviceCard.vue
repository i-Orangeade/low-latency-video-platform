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
  </div>
</template>
