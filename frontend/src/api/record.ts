import { apiGet } from "./client";

export interface RecordItem {
  id: number;
  stream_id: string;
  file_path: string;
  file_name: string;
  duration_seconds: number;
  file_size_bytes: number;
  started_at?: string | null;
  ended_at?: string | null;
  created_at: string;
}

export function listRecords() {
  return apiGet<RecordItem[]>("/records");
}
