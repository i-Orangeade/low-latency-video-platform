<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import {
  createVideoSource,
  deleteVideoSource,
  listVideoSources,
  updateVideoSource,
  type VideoSource
} from "../api/videoSource";
import VideoSourceCard from "../components/VideoSourceCard.vue";

const videoSources = ref<VideoSource[]>([]);
const total = ref(0);
const totalPages = ref(0);
const currentPage = ref(1);
const pageSize = 6;
const searchTerm = ref("");
const appliedQuery = ref("");
const enabledFilter = ref<"all" | "true" | "false">("all");
const isLoading = ref(false);
const isSaving = ref(false);
const actionSourceId = ref<number | null>(null);
const errorMessage = ref("");
const successMessage = ref("");
const editingSourceId = ref<number | null>(null);
const form = reactive({
  name: "",
  stream_id: "",
  enabled: true
});

const isEditing = computed(() => editingSourceId.value !== null);
const formTitle = computed(() => (isEditing.value ? "编辑视频源" : "新增视频源"));

function selectedEnabled(): boolean | undefined {
  if (enabledFilter.value === "all") return undefined;
  return enabledFilter.value === "true";
}

function resetMessages() {
  errorMessage.value = "";
  successMessage.value = "";
}

async function refresh(page = currentPage.value) {
  isLoading.value = true;
  errorMessage.value = "";
  try {
    const response = await listVideoSources({
      q: appliedQuery.value,
      page,
      pageSize,
      enabled: selectedEnabled()
    });
    videoSources.value = response.items;
    total.value = response.total;
    totalPages.value = response.total_pages;
    currentPage.value = response.page;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "视频源列表加载失败";
  } finally {
    isLoading.value = false;
  }
}

function applyFilters() {
  resetMessages();
  appliedQuery.value = searchTerm.value.trim();
  currentPage.value = 1;
  void refresh(1);
}

function clearFilters() {
  searchTerm.value = "";
  enabledFilter.value = "all";
  applyFilters();
}

function resetForm() {
  editingSourceId.value = null;
  form.name = "";
  form.stream_id = "";
  form.enabled = true;
}

function editSource(source: VideoSource) {
  resetMessages();
  editingSourceId.value = source.id;
  form.name = source.name;
  form.stream_id = source.stream_id;
  form.enabled = source.enabled;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function submit() {
  resetMessages();
  isSaving.value = true;
  const sourceId = editingSourceId.value;
  try {
    if (sourceId === null) {
      await createVideoSource(form);
      successMessage.value = "视频源创建成功";
      resetForm();
      await refresh(1);
    } else {
      await updateVideoSource(sourceId, form);
      successMessage.value = "视频源更新成功";
      resetForm();
      await refresh();
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "保存视频源失败";
  } finally {
    isSaving.value = false;
  }
}

async function toggleSource(source: VideoSource) {
  resetMessages();
  actionSourceId.value = source.id;
  try {
    await updateVideoSource(source.id, { enabled: !source.enabled });
    successMessage.value = `${source.name} 已${source.enabled ? "停用" : "启用"}`;
    await refresh();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "更新视频源状态失败";
  } finally {
    actionSourceId.value = null;
  }
}

async function removeSource(source: VideoSource) {
  if (!window.confirm(`确定删除视频源“${source.name}”吗？`)) return;

  resetMessages();
  actionSourceId.value = source.id;
  try {
    await deleteVideoSource(source.id);
    successMessage.value = "视频源已删除";
    const nextPage = videoSources.value.length === 1 && currentPage.value > 1
      ? currentPage.value - 1
      : currentPage.value;
    await refresh(nextPage);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "删除视频源失败";
  } finally {
    actionSourceId.value = null;
  }
}

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  void refresh(page);
}

onMounted(() => void refresh(1));
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <p class="eyebrow">CONTROL PLANE</p>
        <h2 class="page-title">视频源管理</h2>
        <p class="page-description">登记、筛选并维护接入平台的实时视频源。</p>
      </div>
      <span class="count-label">共 {{ total }} 个视频源</span>
    </div>

    <div class="management-layout">
      <form class="panel source-form" @submit.prevent="submit">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">SOURCE FORM</p>
            <h3>{{ formTitle }}</h3>
          </div>
          <button
            v-if="isEditing"
            class="button button--small button--text"
            type="button"
            @click="resetForm"
          >
            取消编辑
          </button>
        </div>
        <label class="field">
          <span>视频源名称</span>
          <input
            v-model="form.name"
            class="input"
            required
            maxlength="100"
            placeholder="例如：前门摄像头"
          >
        </label>
        <label class="field">
          <span>流 ID</span>
          <input
            v-model="form.stream_id"
            class="input"
            required
            maxlength="100"
            pattern="[A-Za-z0-9_-]+"
            placeholder="例如：front_door"
          >
        </label>
        <label class="checkbox-field">
          <input v-model="form.enabled" type="checkbox">
          <span>启用此视频源</span>
        </label>
        <button class="button button--full" type="submit" :disabled="isSaving">
          {{ isSaving ? "保存中..." : isEditing ? "保存修改" : "创建视频源" }}
        </button>
      </form>

      <div class="panel source-list-panel">
        <div class="toolbar">
          <form class="search-form" @submit.prevent="applyFilters">
            <label class="sr-only" for="video-source-search">搜索视频源</label>
            <input
              id="video-source-search"
              v-model="searchTerm"
              class="input"
              type="search"
              placeholder="搜索名称或流 ID"
            >
            <button class="button" type="submit">搜索</button>
          </form>
          <label class="filter-field">
            <span class="sr-only">启用状态</span>
            <select v-model="enabledFilter" class="select" @change="applyFilters">
              <option value="all">全部状态</option>
              <option value="true">仅已启用</option>
              <option value="false">仅已停用</option>
            </select>
          </label>
          <button class="button button--secondary" type="button" @click="clearFilters">
            清除筛选
          </button>
        </div>

        <div v-if="errorMessage" class="notice notice--error" role="alert">
          {{ errorMessage }}
        </div>
        <div v-if="successMessage" class="notice notice--success" role="status">
          {{ successMessage }}
        </div>

        <div v-if="isLoading" class="list-state" role="status" aria-busy="true">
          正在加载视频源...
        </div>
        <div v-else-if="videoSources.length === 0" class="list-state" role="status">
          <strong>没有找到视频源</strong>
          <span>调整搜索条件，或先创建一个新视频源。</span>
        </div>
        <div v-else class="source-grid">
          <VideoSourceCard
            v-for="source in videoSources"
            :key="source.id"
            :source="source"
            :class="{ 'is-busy': actionSourceId === source.id }"
            @edit="editSource(source)"
            @toggle="toggleSource(source)"
            @delete="removeSource(source)"
          />
        </div>

        <div v-if="totalPages > 1" class="pagination" aria-label="视频源分页">
          <button
            class="button button--secondary button--small"
            type="button"
            :disabled="currentPage === 1 || isLoading"
            @click="goToPage(currentPage - 1)"
          >
            上一页
          </button>
          <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
          <button
            class="button button--secondary button--small"
            type="button"
            :disabled="currentPage === totalPages || isLoading"
            @click="goToPage(currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
