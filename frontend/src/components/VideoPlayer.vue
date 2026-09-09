<script setup lang="ts">
import mpegts from "mpegts.js";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{
  url: string;
  protocol: string;
}>();

const videoRef = ref<HTMLVideoElement | null>(null);
const errorMessage = ref("");
const isLoading = ref(false);
let player: mpegts.Player | null = null;
let peerConnection: RTCPeerConnection | null = null;
let abortController: AbortController | null = null;
let loadGeneration = 0;

function releaseResources() {
  abortController?.abort();
  abortController = null;

  if (peerConnection) {
    peerConnection.ontrack = null;
    peerConnection.oniceconnectionstatechange = null;
    peerConnection.close();
    peerConnection = null;
  }

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
  isLoading.value = false;
}

function waitForIceGathering(pc: RTCPeerConnection): Promise<void> {
  if (pc.iceGatheringState === "complete") {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    const timeoutId = window.setTimeout(() => {
      pc.removeEventListener("icegatheringstatechange", handleStateChange);
      reject(new Error("ICE 候选收集超时"));
    }, 10_000);

    function handleStateChange() {
      if (pc.iceGatheringState !== "complete") {
        return;
      }
      window.clearTimeout(timeoutId);
      pc.removeEventListener("icegatheringstatechange", handleStateChange);
      resolve();
    }

    pc.addEventListener("icegatheringstatechange", handleStateChange);
  });
}

async function playVideo(video: HTMLVideoElement) {
  try {
    await video.play();
  } catch {
    // 浏览器仍可通过原生 controls 手动开始播放。
  }
}

function loadFlv(video: HTMLVideoElement) {
  if (!mpegts.getFeatureList().mseLivePlayback) {
    throw new Error("当前浏览器不支持 HTTP-FLV 的 MSE 播放");
  }

  player = mpegts.createPlayer({
    type: "flv",
    isLive: true,
    url: props.url
  });
  player.attachMediaElement(video);
  player.load();
  void playVideo(video);
}

function loadHls(video: HTMLVideoElement) {
  if (!video.canPlayType("application/vnd.apple.mpegurl")) {
    throw new Error("当前浏览器不支持原生 HLS 播放");
  }

  video.src = props.url;
  video.load();
  void playVideo(video);
}

async function loadWebRtc(video: HTMLVideoElement, generation: number) {
  const endpoint = new URL(props.url, window.location.href);
  endpoint.searchParams.set("type", "play");

  const pc = new RTCPeerConnection();
  const controller = new AbortController();
  const incomingStream = new MediaStream();
  peerConnection = pc;
  abortController = controller;

  pc.addTransceiver("audio", { direction: "recvonly" });
  pc.addTransceiver("video", { direction: "recvonly" });

  pc.ontrack = (event: RTCTrackEvent) => {
    if (generation !== loadGeneration) {
      return;
    }

    const stream = event.streams[0];
    if (stream) {
      video.srcObject = stream;
    } else {
      incomingStream.addTrack(event.track);
      video.srcObject = incomingStream;
    }
    void playVideo(video);
  };

  pc.oniceconnectionstatechange = () => {
    if (
      generation === loadGeneration &&
      (pc.iceConnectionState === "failed" || pc.iceConnectionState === "disconnected")
    ) {
      errorMessage.value = `WebRTC ICE 连接${pc.iceConnectionState === "failed" ? "失败" : "已断开"}`;
    }
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  await waitForIceGathering(pc);

  if (generation !== loadGeneration || !pc.localDescription?.sdp) {
    return;
  }

  const response = await fetch(endpoint.toString(), {
    method: "POST",
    headers: {
      "Content-Type": "text/plain;charset=UTF-8"
    },
    body: pc.localDescription.sdp,
    signal: controller.signal
  });

  if (!response.ok) {
    throw new Error(`ZLMediaKit WebRTC 接口返回 HTTP ${response.status}`);
  }

  const answer = (await response.json()) as {
    code?: number;
    msg?: string;
    sdp?: string;
  };
  if (answer.code !== 0) {
    throw new Error(answer.msg || `ZLMediaKit WebRTC 协商失败（code=${answer.code ?? "unknown"}）`);
  }
  if (!answer.sdp?.trim()) {
    throw new Error("ZLMediaKit WebRTC 接口返回了空 SDP");
  }
  if (generation !== loadGeneration) {
    return;
  }

  await pc.setRemoteDescription({
    type: "answer",
    sdp: answer.sdp
  });
}

async function loadPlayer() {
  const generation = ++loadGeneration;
  releaseResources();
  errorMessage.value = "";
  isLoading.value = false;

  const video = videoRef.value;
  if (!video || !props.url) {
    return;
  }

  isLoading.value = true;
  try {
    if (props.protocol === "flv") {
      loadFlv(video);
    } else if (props.protocol === "webrtc") {
      await loadWebRtc(video, generation);
    } else if (props.protocol === "hls") {
      loadHls(video);
    } else {
      throw new Error(`浏览器不支持直接播放 ${props.protocol.toUpperCase()} 协议`);
    }
  } catch (error) {
    if (
      generation === loadGeneration &&
      !(error instanceof DOMException && error.name === "AbortError")
    ) {
      errorMessage.value = error instanceof Error ? error.message : "播放器加载失败";
      releaseResources();
    }
  } finally {
    if (generation === loadGeneration) {
      isLoading.value = false;
    }
  }
}

watch(() => [props.url, props.protocol], () => void loadPlayer());
onMounted(() => void loadPlayer());
onBeforeUnmount(destroyPlayer);
</script>

<template>
  <div class="video-player">
    <video ref="videoRef" controls muted playsinline />
    <div v-if="isLoading" class="protocol-note">正在连接 {{ protocol.toUpperCase() }} 播放流…</div>
    <div v-else-if="errorMessage" class="protocol-note error" role="alert">
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
