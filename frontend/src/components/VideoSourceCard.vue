<script setup lang="ts">
import type { VideoSource } from "../api/videoSource";

defineProps<{
  source: VideoSource;
}>();

const emit = defineEmits<{
  edit: [];
  delete: [];
  toggle: [];
}>();

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
</script>

<template>
  <article class="source-card">
    <div class="source-card__header">
      <div>
        <h3>{{ source.name }}</h3>
        <p class="source-card__stream">流 ID：{{ source.stream_id }}</p>
      </div>
      <span
        class="status-badge"
        :class="source.enabled ? 'status-badge--enabled' : 'status-badge--disabled'"
      >
        {{ source.enabled ? "已启用" : "已停用" }}
      </span>
    </div>
    <dl class="source-card__meta">
      <div>
        <dt>更新时间</dt>
        <dd>{{ formatDate(source.updated_at) }}</dd>
      </div>
      <div>
        <dt>视频源 ID</dt>
        <dd>#{{ source.id }}</dd>
      </div>
    </dl>
    <div class="source-card__actions">
      <button class="button button--small" type="button" @click="emit('edit')">
        编辑
      </button>
      <button class="button button--small button--secondary" type="button" @click="emit('toggle')">
        {{ source.enabled ? "停用" : "启用" }}
      </button>
      <button class="button button--small button--danger" type="button" @click="emit('delete')">
        删除
      </button>
    </div>
  </article>
</template>
