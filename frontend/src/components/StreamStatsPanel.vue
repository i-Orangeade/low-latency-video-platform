<script setup lang="ts">
import type { StreamStatus } from "../api/stream";

defineProps<{
  status: StreamStatus | null;
}>();
</script>

<template>
  <div class="card stats-panel">
    <h3>链路状态</h3>
    <p>
      在线状态：
      <span :class="status?.online ? 'status-online' : 'status-offline'">
        {{ status?.online ? "在线" : "离线" }}
      </span>
    </p>
    <p>应用名：{{ status?.app ?? "-" }}</p>
    <p>来源协议：{{ status?.schema_name ?? "-" }}</p>
    <p>来源类型：{{ status?.origin_type ?? "-" }}</p>
    <p>当前观看数：{{ status?.reader_count ?? 0 }}</p>
    <p>累计观看数：{{ status?.total_reader_count ?? 0 }}</p>
    <p>Track 数：{{ status?.tracks.length ?? 0 }}</p>
  </div>
</template>

<style scoped>
.stats-panel h3 {
  margin-top: 0;
}
</style>
