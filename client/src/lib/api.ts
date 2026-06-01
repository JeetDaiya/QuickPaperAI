import type {
  GenerateRequest,
  GenerateResponse,
  ResumePayload,
  StatusResponse,
} from "./types";

// QuickPaperAI client — calls the FastAPI backend directly from the browser.
// Override the base via VITE_API_BASE_URL.
export const API_BASE: string =
  (typeof import.meta !== "undefined" &&
    (import.meta as ImportMeta & { env?: Record<string, string> }).env
      ?.VITE_API_BASE_URL) ||
  "http://localhost:8000";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      `API ${path} → ${res.status} ${res.statusText}${body ? `: ${body.slice(0, 200)}` : ""}`,
    );
  }
  return res.json() as Promise<T>;
}

export const api = {
  generate: (payload: GenerateRequest) =>
    jsonFetch<GenerateResponse>("/api/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getChapters: () =>
    jsonFetch<{
      chapters: { chapter_name: string; subject: string; standard: string }[];
    }>("/api/db/get-chapters"),

  status: (threadId: string) =>
    jsonFetch<StatusResponse>(`/api/status/${encodeURIComponent(threadId)}`),

  resume: (threadId: string, payload: ResumePayload) =>
    jsonFetch<{ ok: true }>(`/api/resume/${encodeURIComponent(threadId)}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  saveToCloud: (threadId: string) =>
    jsonFetch<{ status: string }>(`/api/save-to-cloud/${encodeURIComponent(threadId)}`, {
      method: "POST",
    }),

  // The backend already returns absolute-relative paths for files, e.g.
  // "/api/download/<thread>/paper.pdf". Just join with the base.
  fileUrl: (apiPath: string) =>
    apiPath.startsWith("http") ? apiPath : `${API_BASE}${apiPath}`,
};
