import { apiGet } from "./client";

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
