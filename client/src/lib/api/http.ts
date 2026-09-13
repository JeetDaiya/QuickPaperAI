// The only module that knows about HTTP. Ported from the old client's jsonFetch
// (QuickPaperAI/client/src/lib/api.ts), ported logic only — none of its UI.

import type { ApiErrorCode } from "./types";

// Config comes from `.env` only (see `.env.example`). A production build with no
// VITE_API_BASE_URL fails at startup rather than silently shipping a bundle pointed at
// localhost; dev keeps the localhost default so `npm run dev` works out of the box.
const configured = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();

if (!configured && import.meta.env.PROD) {
  throw new Error("VITE_API_BASE_URL is not set — set it in .env before building for production.");
}

let base: string = configured || "http://localhost:8000";

if (!configured) {
  console.warn("VITE_API_BASE_URL is not set — falling back to http://localhost:8000 (dev only).");
}

if (!base.startsWith("http://") && !base.startsWith("https://")) {
  base = `https://${base}`;
}

export const API_BASE: string = base;

export function getToken(): string | null {
  return typeof window !== "undefined" ? localStorage.getItem("token") : null;
}

export function setToken(token: string): void {
  localStorage.setItem("token", token);
}

export function clearToken(): void {
  localStorage.removeItem("token");
}

function handle401() {
  clearToken();
  if (typeof window !== "undefined" && window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
    window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}&message=auth_required`;
  }
}

/** Error subclass that preserves the backend's machine-readable `code` (when present)
 * and HTTP status alongside the human-readable message. Fully backward-compatible:
 * extends Error, so every existing `e.message` / `.error?.message` site keeps working.
 * Use `isApiError(e)` to narrow when you need to branch on `code`. */
export class ApiError extends Error {
  readonly code: ApiErrorCode | undefined;
  readonly status: number;
  constructor(message: string, code: ApiErrorCode | undefined, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

async function extractErrorBody(res: Response): Promise<{ detail: string; code?: ApiErrorCode }> {
  const body = await res.text().catch(() => "");
  try {
    const parsed = JSON.parse(body);
    const code = typeof parsed.code === "string" ? (parsed.code as ApiErrorCode) : undefined;
    if (typeof parsed.detail === "string") return { detail: parsed.detail, code };
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      return { detail: parsed.detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(", "), code };
    }
    if (parsed.message) return { detail: parsed.message, code };
    const fallback = typeof parsed === "string" ? parsed : body;
    return { detail: fallback, code };
  } catch {
    return { detail: body };
  }
}

export async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    handle401();
    throw new ApiError("Session expired. Please log in again.", "UNAUTHENTICATED", 401);
  }

  if (!res.ok) {
    const { detail, code } = await extractErrorBody(res);
    throw new ApiError(detail || `${res.status} ${res.statusText}`, code, res.status);
  }

  return res.json() as Promise<T>;
}

/** OAuth2 password-form login — the only endpoint that isn't JSON in, per the contract. */
export async function formFetch<T>(path: string, params: Record<string, string>): Promise<T> {
  const body = new URLSearchParams(params);
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body,
  });

  if (!res.ok) {
    const { detail, code } = await extractErrorBody(res);
    throw new ApiError(detail || `${res.status} ${res.statusText}`, code, res.status);
  }

  return res.json() as Promise<T>;
}

/** Append the auth token to a URL used outside `fetch` (SSE, direct file links) — `&` if a query already exists, per the backend gotcha. */
export function withToken(url: string): string {
  const token = getToken();
  if (!token) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}token=${encodeURIComponent(token)}`;
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Resolves a backend-provided relative path (e.g. `history[].paper_pdf`, `completed.files.paper_pdf`)
 * into a full, token-bearing URL suitable for a direct `<a href>`/`<iframe src>`. */
export function resolveFileUrl(path: string): string {
  return withToken(apiUrl(path));
}
