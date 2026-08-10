<script setup lang="ts">
import { onMounted, ref } from "vue";

import { createTestAlert, type Alert, listAlerts } from "../api/alert";
import AlertTable from "../components/AlertTable.vue";

const alerts = ref<Alert[]>([]);

async function refresh() {
  alerts.value = await listAlerts().catch(() => []);
}

async function addTestAlert() {
  await createTestAlert();
  await refresh();
}

onMounted(refresh);
</script>

<template>
  <section>
    <h2 class="page-title">告警中心</h2>
    <button class="button" style="margin-bottom: 16px" @click="addTestAlert">生成测试告警</button>
    <AlertTable :alerts="alerts" />
  </section>
</template>
