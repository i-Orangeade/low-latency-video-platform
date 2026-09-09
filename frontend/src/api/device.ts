import { apiGet, apiPost } from "./client";

export interface Device {
  id: number;
  name: string;
  stream_id: string;
}

export interface DeviceCreate {
  name: string;
  stream_id: string;
}

export function listDevices() {
  return apiGet<Device[]>("/devices");
}

export function createDevice(payload: DeviceCreate) {
  return apiPost<Device>("/devices", payload);
}
