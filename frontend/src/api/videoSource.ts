import { apiGet, apiPost } from "./client";

export interface VideoSource {
  id: number;
  name: string;
  stream_id: string;
}

export interface VideoSourceCreate {
  name: string;
  stream_id: string;
}

export interface VideoSourceStatus extends VideoSource {
  online: boolean;
  app: string;
  schema_name: string | null;
  origin_type: string | null;
  reader_count: number;
  total_reader_count: number;
  tracks: Record<string, unknown>[];
}

export interface VideoSourceStatusSummary {
  total: number;
  online: number;
  offline: number;
  video_sources: VideoSourceStatus[];
}

export function listVideoSources() {
  return apiGet<VideoSource[]>("/video-sources");
}

export function getVideoSourceStatusSummary() {
  return apiGet<VideoSourceStatusSummary>("/video-sources/status");
}

export function createVideoSource(payload: VideoSourceCreate) {
  return apiPost<VideoSource>("/video-sources", payload);
}
