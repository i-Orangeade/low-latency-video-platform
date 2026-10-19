<script setup lang="ts">
import { ref, watch } from "vue";

const props = defineProps<{
  url: string;
}>();

const copyState = ref<"idle" | "copied" | "failed">("idle");

watch(
  () => props.url,
  () => {
    copyState.value = "idle";
  }
);

async function copyShareUrl() {
  if (!props.url) return;

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(props.url);
    } else {
      const input = document.createElement("textarea");
      input.value = props.url;
      input.readOnly = true;
      input.style.position = "fixed";
      input.style.opacity = "0";
      document.body.appendChild(input);
      input.select();
      const copied = document.execCommand("copy");
      input.remove();
      if (!copied) throw new Error("copy failed");
    }
    copyState.value = "copied";
  } catch {
    copyState.value = "failed";
  }
}
</script>

<template>
  <div class="card share-panel">
    <h3>分享播放</h3>
    <label class="share-panel__label" for="share-url">播放地址</label>
    <div class="share-panel__controls">
      <input
        id="share-url"
        class="input"
        :value="url"
        readonly
        placeholder="选择视频源后生成"
      >
      <button class="button" type="button" :disabled="!url" @click="copyShareUrl">
        {{ copyState === "copied" ? "已复制" : "复制链接" }}
      </button>
    </div>
    <p v-if="copyState === 'failed'" class="share-panel__status" role="alert">
      复制失败，请手动选择地址。
    </p>
  </div>
</template>

<style scoped>
.share-panel h3 {
  margin-top: 0;
}

.share-panel__label {
  display: block;
  margin-bottom: 8px;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.share-panel__controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.share-panel__status {
  margin: 8px 0 0;
  color: #b91c1c;
  font-size: 13px;
}
</style>
