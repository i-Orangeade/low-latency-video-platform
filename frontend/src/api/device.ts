import { apiGet, apiPost } from "./client";

// 与后端 schemas/device.py 对应的前端数据类型和请求函数。
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
