<script setup lang="ts">
import type { Alert } from "../api/alert";

defineProps<{
  alerts: Alert[];
}>();
</script>

<template>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th>时间</th>
          <th>流 ID</th>
          <th>级别</th>
          <th>类型</th>
          <th>内容</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="alert in alerts" :key="alert.id">
          <td>{{ new Date(alert.created_at).toLocaleString() }}</td>
          <td>{{ alert.stream_id }}</td>
          <td>{{ alert.level }}</td>
          <td>{{ alert.category }}</td>
          <td>{{ alert.message }}</td>
          <td>{{ alert.is_read ? "已读" : "未读" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  padding: 10px;
  text-align: left;
}
</style>
