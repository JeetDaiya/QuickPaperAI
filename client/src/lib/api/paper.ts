import { jsonFetch, apiUrl, withToken } from "./http";
import type {
  PaperGenerateRequest,
  GenerateResponse,
  ResumeResponse,
  SaveToCloudResponse,
  CancelResponse,
} from "./types";

export function generatePaper(payload: PaperGenerateRequest) {
  return jsonFetch<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resumeGeneration(threadId: string, selectedIndices: number[]) {
  return jsonFetch<ResumeResponse>(`/api/resume/${encodeURIComponent(threadId)}`, {
    method: "POST",
    body: JSON.stringify({ selected_indices: selectedIndices }),
  });
}

/** SSE endpoint — there is no plain JSON GET /api/status/{threadId}, only /stream. */
export function statusStreamUrl(threadId: string): string {
  return withToken(apiUrl(`/api/status/${encodeURIComponent(threadId)}/stream`));
}

/** Direct file link (download/preview) — token must ride in the query string, not a header. */
export function downloadFileUrl(threadId: string, filename: string, preview = false): string {
  const path = `/api/download/${encodeURIComponent(threadId)}/${encodeURIComponent(filename)}${preview ? "?preview=true" : ""}`;
  return withToken(apiUrl(path));
}

export function saveToCloud(threadId: string) {
  return jsonFetch<SaveToCloudResponse>(`/api/save-to-cloud/${encodeURIComponent(threadId)}`, {
    method: "POST",
  });
}

export function cancelGeneration(threadId: string) {
  return jsonFetch<CancelResponse>(`/api/cancel/${encodeURIComponent(threadId)}`, {
    method: "DELETE",
  });
}
