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

export function getPlayUrl(streamId: string, protocol: StreamProtocol) {
  return apiGet<PlayUrlResponse>(`/streams/${streamId}/play-url?protocol=${protocol}`);
}

export function getStreamStatus(streamId: string) {
  return apiGet<StreamStatus>(`/streams/${streamId}/status`);
}

export function startRecord(streamId: string) {
  return apiPost<Record<string, unknown>>(`/streams/${streamId}/start-record`);
}

export function stopRecord(streamId: string) {
  return apiPost<Record<string, unknown>>(`/streams/${streamId}/stop-record`);
}
