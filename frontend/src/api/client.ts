// 前端 API 基础封装。
// 页面只调用 apiGet/apiPost，不直接拼接 FastAPI 的 host 和端口，因此开发、Docker 和生产代理
// 可以使用同一份业务代码。开发环境由 Vite 代理 /api，生产环境由 Nginx 转发。
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) {
    throw new Error(`POST ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
