<script setup lang="ts">
import type { StreamQos, StreamStatus } from "../api/stream";

defineProps<{
  status: StreamStatus | null;
  qos: StreamQos | null;
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
    <template v-if="qos">
      <h3>自定义 ZLM QoS</h3>
      <p>采样窗口：{{ qos.probe_ms }} ms</p>
      <p>视频帧率：{{ qos.video_fps.toFixed(2) }} fps</p>
      <p>采样码率：{{ qos.bitrate_kbps.toFixed(2) }} kbit/s</p>
      <p>关键帧数：{{ qos.key_frame_count }}</p>
      <p>平均 GOP：{{ qos.average_gop_ms?.toFixed(1) ?? "-" }} ms</p>
      <p>采样首帧：{{ qos.first_frame_delay_ms ?? "-" }} ms</p>
      <p>时间戳回退：{{ qos.timestamp_rollback_count }}</p>
    </template>
  </div>
</template>

<style scoped>
.stats-panel h3 {
  margin-top: 0;
}
</style>
