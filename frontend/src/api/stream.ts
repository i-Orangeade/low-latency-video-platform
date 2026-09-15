import { apiGet } from "./client";

// 与后端 schemas/stream.py 对应。
// play-url 只返回地址，stream status 返回 ZLM 当前是否在线及观看统计。
export interface PlayUrlResponse {
  stream_id: string;
  protocol: string;
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

export function getPlayUrl(streamId: string) {
  return apiGet<PlayUrlResponse>(`/streams/${streamId}/play-url`);
}

export function getStreamStatus(streamId: string) {
  return apiGet<StreamStatus>(`/streams/${streamId}/status`);
}
