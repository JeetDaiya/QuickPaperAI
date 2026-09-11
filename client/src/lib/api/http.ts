// The only module that knows about HTTP. Ported from the old client's jsonFetch
// (QuickPaperAI/client/src/lib/api.ts), ported logic only — none of its UI.

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

async function extractErrorDetail(res: Response): Promise<string> {
  const body = await res.text().catch(() => "");
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      return parsed.detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(", ");
    }
    if (parsed.message) return parsed.message;
    return typeof parsed === "string" ? parsed : body;
  } catch {
    return body;
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
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const detail = await extractErrorDetail(res);
    throw new Error(detail || `${res.status} ${res.statusText}`);
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
    const detail = await extractErrorDetail(res);
    throw new Error(detail || `${res.status} ${res.statusText}`);
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
