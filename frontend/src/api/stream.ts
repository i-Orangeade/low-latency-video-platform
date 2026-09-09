import { apiGet, apiPost } from "./client";

export type StreamProtocol = "flv" | "webrtc" | "hls" | "rtmp" | "rtsp";

export interface PlayUrlResponse {
  stream_id: string;
  protocol: StreamProtocol;
  url: string;
}

export interface StreamStatus {
  stream_id: string;
  online: boolean;
  app: string;
  schema_name?: string | null;
  origin_type?: string | null;
  reader_count: number;
  total_reader_count: number;
  tracks: Record<string, unknown>[];
}

export interface StreamQos {
  stream_id: string;
  probe_ms: number;
  bitrate_kbps: number;
  video_fps: number;
  video_frame_count: number;
  audio_frame_count: number;
  key_frame_count: number;
  average_gop_ms?: number | null;
  first_frame_delay_ms?: number | null;
  timestamp_rollback_count: number;
  reader_count: number;
  total_reader_count: number;
  current_bytes_speed: number;
  alive_second: number;
}

export function getPlayUrl(streamId: string, protocol: StreamProtocol) {
  return apiGet<PlayUrlResponse>(`/streams/${streamId}/play-url?protocol=${protocol}`);
}

export function getStreamStatus(streamId: string) {
  return apiGet<StreamStatus>(`/streams/${streamId}/status`);
}

export function getStreamQos(streamId: string, probeMs = 1000) {
  return apiGet<StreamQos>(`/streams/${streamId}/qos?probe_ms=${probeMs}`);
}

export function startRecord(streamId: string) {
  return apiPost<Record<string, unknown>>(`/streams/${streamId}/start-record`);
}

export function stopRecord(streamId: string) {
  return apiPost<Record<string, unknown>>(`/streams/${streamId}/stop-record`);
}
