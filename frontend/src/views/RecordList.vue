<script setup lang="ts">
import { onMounted, ref } from "vue";

import { listRecords, type RecordItem } from "../api/record";

const records = ref<RecordItem[]>([]);

onMounted(async () => {
  records.value = await listRecords().catch(() => []);
});
</script>

<template>
  <section>
    <h2 class="page-title">录像回放</h2>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>流 ID</th>
            <th>文件名</th>
            <th>时长</th>
            <th>大小</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td>{{ record.stream_id }}</td>
            <td>{{ record.file_name }}</td>
            <td>{{ record.duration_seconds }} s</td>
            <td>{{ (record.file_size_bytes / 1024 / 1024).toFixed(2) }} MB</td>
            <td>{{ new Date(record.created_at).toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
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
