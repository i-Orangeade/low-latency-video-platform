import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export interface VideoSource {
  id: number;
  name: string;
  stream_id: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface VideoSourcePage {
  items: VideoSource[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface VideoSourceCreate {
  name: string;
  stream_id: string;
  enabled?: boolean;
}

export interface VideoSourceUpdate {
  name?: string;
  stream_id?: string;
  enabled?: boolean;
}

export interface VideoSourceStatus extends Pick<VideoSource, "id" | "name" | "stream_id"> {
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

export interface VideoSourceListParams {
  q?: string;
  page?: number;
  pageSize?: number;
  enabled?: boolean;
}

export function listVideoSources(params: VideoSourceListParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set("q", params.q);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.pageSize) searchParams.set("page_size", String(params.pageSize));
  if (params.enabled !== undefined) searchParams.set("enabled", String(params.enabled));

  const query = searchParams.toString();
  return apiGet<VideoSourcePage>(`/video-sources${query ? `?${query}` : ""}`);
}

export function getVideoSourceStatusSummary() {
  return apiGet<VideoSourceStatusSummary>("/video-sources/status");
}

export function createVideoSource(payload: VideoSourceCreate) {
  return apiPost<VideoSource>("/video-sources", payload);
}

export function updateVideoSource(sourceId: number, payload: VideoSourceUpdate) {
  return apiPut<VideoSource>(`/video-sources/${sourceId}`, payload);
}

export function deleteVideoSource(sourceId: number) {
  return apiDelete(`/video-sources/${sourceId}`);
}
