import { apiGet, apiPost } from "./client";

export interface Alert {
  id: number;
  stream_id: string;
  level: string;
  category: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export function listAlerts() {
  return apiGet<Alert[]>("/alerts");
}

export function createTestAlert() {
  return apiPost<Alert>("/alerts/test");
}
