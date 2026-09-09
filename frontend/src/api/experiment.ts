import { apiGet, apiPost } from "./client";

export interface Experiment {
  id: number;
  name: string;
  stream_id: string;
  protocol: string;
  network_profile: string;
  encoder_params?: string | null;
  avg_latency_ms?: number | null;
  max_latency_ms?: number | null;
  p50_latency_ms?: number | null;
  p95_latency_ms?: number | null;
  p99_latency_ms?: number | null;
  sample_count: number;
  measurement_method?: string | null;
  bitrate_kbps?: number | null;
  fps?: number | null;
  stutter_count: number;
  created_at: string;
}

export function listExperiments() {
  return apiGet<Experiment[]>("/experiments");
}

export function createLatencyExperiment(payload: Omit<Experiment, "id" | "created_at">) {
  return apiPost<Experiment>("/experiments/latency", payload);
}
