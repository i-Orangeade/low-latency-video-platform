<script setup lang="ts">
// HTTP-FLV 播放器封装。
// 数据流：父组件提供 playUrl -> mpegts.js 拉取 FLV -> MSE 解码 -> video 元素播放。
// 组件只负责播放，不负责向后端查询地址或状态。
import mpegts from "mpegts.js";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

type PlayerState = "idle" | "connecting" | "playing" | "buffering" | "error" | "ended";

const props = defineProps<{
  url: string;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
const playerState = ref<PlayerState>("idle");
const errorMessage = ref("");
let player: mpegts.Player | null = null;
let videoEventCleanup: (() => void) | null = null;
// 快速切换地址时，旧异步任务可能晚于新任务返回。
// 每次加载递增 generation，旧任务发现代次不匹配后不会再修改页面状态。
let loadGeneration = 0;

const isActiveState = (generation: number) => generation === loadGeneration;

function setPlayerError(message: string, generation = loadGeneration) {
  if (!isActiveState(generation)) return;
  playerState.value = "error";
  errorMessage.value = message;
}

function describeMpegtsError(errorType?: string, errorDetail?: string) {
  if (errorType === mpegts.ErrorTypes.NETWORK_ERROR) {
    return `网络错误${errorDetail ? `（${errorDetail}）` : ""}`;
  }
  if (errorType === mpegts.ErrorTypes.MEDIA_ERROR) {
    return `媒体解码错误${errorDetail ? `（${errorDetail}）` : ""}`;
  }
  return `播放器错误${errorDetail ? `（${errorDetail}）` : ""}`;
}

function handlePlayerError(
  errorType: string,
  errorDetail: string,
  errorInfo: unknown,
  generation: number
) {
  if (!isActiveState(generation)) return;
  console.warn("[VideoPlayer] mpegts.js error", {
    errorType,
    errorDetail,
    errorInfo
  });
  setPlayerError(describeMpegtsError(errorType, errorDetail), generation);
  releaseResources();
}

function bindPlayerEvents(instance: mpegts.Player, generation: number) {
  instance.on(mpegts.Events.ERROR, (errorType, errorDetail, errorInfo) => {
    handlePlayerError(errorType, errorDetail, errorInfo, generation);
  });
  instance.on(mpegts.Events.LOADING_COMPLETE, () => {
    if (!isActiveState(generation)) return;
    playerState.value = "ended";
    errorMessage.value = "播放流已结束或连接已关闭";
  });
  instance.on(mpegts.Events.RECOVERED_EARLY_EOF, () => {
    if (!isActiveState(generation)) return;
    playerState.value = "buffering";
    errorMessage.value = "播放流暂时中断，等待媒体数据";
  });
  instance.on(mpegts.Events.MEDIA_INFO, () => {
    if (!isActiveState(generation)) return;
    errorMessage.value = "";
  });
}

function bindVideoEvents(video: HTMLVideoElement, generation: number) {
  const onPlaying = () => {
    if (!isActiveState(generation)) return;
    playerState.value = "playing";
    errorMessage.value = "";
  };
  const onWaiting = () => {
    if (!isActiveState(generation)) return;
    playerState.value = "buffering";
  };
  const onStalled = () => {
    if (!isActiveState(generation)) return;
    playerState.value = "buffering";
    errorMessage.value = "播放流暂时没有数据";
  };
  const onEnded = () => {
    if (!isActiveState(generation)) return;
    playerState.value = "ended";
    errorMessage.value = "播放流已结束";
  };
  const onError = () => {
    if (!isActiveState(generation)) return;
    setPlayerError("浏览器无法解码此播放流", generation);
    releaseResources();
  };

  video.addEventListener("playing", onPlaying);
  video.addEventListener("waiting", onWaiting);
  video.addEventListener("stalled", onStalled);
  video.addEventListener("ended", onEnded);
  video.addEventListener("error", onError);
  videoEventCleanup = () => {
    video.removeEventListener("playing", onPlaying);
    video.removeEventListener("waiting", onWaiting);
    video.removeEventListener("stalled", onStalled);
    video.removeEventListener("ended", onEnded);
    video.removeEventListener("error", onError);
  };
}

function releaseResources() {
  videoEventCleanup?.();
  videoEventCleanup = null;

  // mpegts 播放器和 video 元素必须同时释放，否则会保留旧连接和媒体缓冲。
  if (player) {
    player.destroy();
    player = null;
  }

  if (videoRef.value) {
    videoRef.value.pause();
    videoRef.value.removeAttribute("src");
    videoRef.value.srcObject = null;
    videoRef.value.load();
  }
}

function destroyPlayer() {
  loadGeneration += 1;
  releaseResources();
  playerState.value = "idle";
}

async function playVideo(video: HTMLVideoElement) {
  try {
    await video.play();
  } catch {
    // 浏览器可能要求用户手势或禁止自动播放；保留原生 controls 让用户手动开始。
  }
}

function loadFlv(video: HTMLVideoElement) {
  if (!mpegts.getFeatureList().mseLivePlayback) {
    throw new Error("当前浏览器不支持 HTTP-FLV 的 MSE 播放");
  }

  // mpegts.js 通过 Media Source Extensions 拉取并解码 HTTP-FLV 直播流。
  player = mpegts.createPlayer({
    type: "flv",
    isLive: true,
    url: props.url
  });
  const generation = loadGeneration;
  bindPlayerEvents(player, generation);
  bindVideoEvents(video, generation);
  player.attachMediaElement(video);
  player.load();
  void playVideo(video);
}

async function loadPlayer() {
  // 每次切换 URL 都先释放旧播放器，再创建新连接，避免多个 FLV 流同时占用资源。
  const generation = ++loadGeneration;
  releaseResources();
  errorMessage.value = "";
  playerState.value = "idle";

  const video = videoRef.value;
  if (!video || !props.url) {
    return;
  }

  playerState.value = "connecting";
  try {
    loadFlv(video);
  } catch (error) {
    // 只有当前代次仍是最新任务时才展示错误，避免旧请求覆盖新请求的页面状态。
    if (isActiveState(generation)) {
      setPlayerError(error instanceof Error ? error.message : "播放器加载失败", generation);
      releaseResources();
    }
  }
}

watch(
  () => props.url,
  () => void loadPlayer()
);

// 页面首次打开时需要主动加载；组件销毁时必须释放网络连接和媒体缓冲。
onMounted(() => void loadPlayer());
onBeforeUnmount(destroyPlayer);
</script>

<template>
  <div class="video-player">
    <video ref="videoRef" controls muted playsinline />
    <div v-if="playerState === 'connecting'" class="protocol-note">
      正在连接 HTTP-FLV 播放流…
    </div>
    <div v-else-if="playerState === 'buffering'" class="protocol-note">
      {{ errorMessage || "正在缓冲播放流…" }}
    </div>
    <div v-else-if="playerState === 'error' || playerState === 'ended'" class="protocol-note error" role="alert">
      {{ errorMessage }}
    </div>
  </div>
</template>

<style scoped>
.video-player {
  overflow: hidden;
  border-radius: 14px;
  background: #0f172a;
}

video {
  display: block;
  width: 100%;
  min-height: 420px;
  background: #0f172a;
}

.protocol-note {
  padding: 14px;
  color: #e2e8f0;
  line-height: 1.7;
}

.protocol-note.error {
  color: #fecaca;
  background: rgb(127 29 29 / 35%);
}
</style>
