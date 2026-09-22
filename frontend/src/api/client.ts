// 前端 API 基础封装。
// 页面只调用 apiGet/apiPost，不直接拼接 FastAPI 的 host 和端口，因此开发、Docker 和生产代理
// 可以使用同一份业务代码。开发环境由 Vite 代理 /api，生产环境由 Nginx 转发。
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function errorFromResponse(method: string, path: string, response: Response): Promise<Error> {
  let detail = "";
  try {
    const payload = await response.json() as {
      detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
    };
    if (typeof payload.detail === "string") {
      detail = payload.detail;
    } else if (Array.isArray(payload.detail)) {
      detail = payload.detail
        .map((item) => {
          const field = item.loc?.[item.loc.length - 1];
          return field ? `${field}: ${item.msg ?? "参数无效"}` : item.msg ?? "参数无效";
        })
        .join("；");
    }
  } catch {
    // Some proxy errors do not return JSON; keep the status as the fallback.
  }
  return new Error(
    `${method} ${path} failed: ${response.status}${detail ? ` - ${detail}` : ""}`
  );
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw await errorFromResponse("GET", path, response);
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
    throw await errorFromResponse("POST", path, response);
  }
  return response.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw await errorFromResponse("PUT", path, response);
  }
  return response.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw await errorFromResponse("DELETE", path, response);
  }
}
