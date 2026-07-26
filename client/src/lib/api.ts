import type {
  GenerateRequest,
  GenerateResponse,
  ResumePayload,
  StatusResponse,
} from "./types";

// QuickPaperAI client — calls the FastAPI backend directly from the browser.
// Override the base via VITE_API_BASE_URL.
let base =
  (typeof import.meta !== "undefined" &&
    (import.meta as ImportMeta & { env?: Record<string, string> }).env
      ?.VITE_API_BASE_URL) ||
  "http://localhost:8000";

if (base && !base.startsWith("http://") && !base.startsWith("https://")) {
  base = `https://${base}`;
}

export const API_BASE: string = base;

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(init?.headers as Record<string, string> ?? {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}&message=auth_required`;
      }
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let errorDetail = "";
    try {
      const parsed = JSON.parse(body);
      if (typeof parsed.detail === "string") {
        errorDetail = parsed.detail;
      } else if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
        errorDetail = parsed.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
      } else if (parsed.message) {
        errorDetail = parsed.message;
      } else {
        errorDetail = typeof parsed === "string" ? parsed : body;
      }
    } catch {
      errorDetail = body;
    }
    throw new Error(errorDetail || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  register: (payload: Record<string, any>) =>
    jsonFetch<any>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  sendOtp: (payload: { email: string; purpose?: "signup" | "reset_password" }) =>
    jsonFetch<{ message: string }>("/auth/send-email", {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        purpose: payload.purpose || "signup",
      }),
    }),

  verifyOtp: (payload: { email: string; otp: string; purpose?: "signup" | "reset_password" }) =>
    jsonFetch<{
      message: string;
      access_token?: string;
      token_type?: string;
      reset_token?: string;
    }>("/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        otp: String(payload.otp),
        purpose: payload.purpose || "signup",
      }),
    }),

  resetPassword: (payload: { email: string; token: string; new_password: string }) =>
    jsonFetch<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        token: payload.token,
        new_password: payload.new_password,
      }),
    }),

  login: (payload: Record<string, any>) => {
    const params = new URLSearchParams();
    params.append("username", payload.email);
    params.append("password", payload.password);

    return fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/json",
      },
      body: params,
    }).then(async (res) => {
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        let errorDetail = "";
        try {
          const parsed = JSON.parse(body);
          errorDetail = parsed.detail || "";
        } catch {
          errorDetail = body;
        }
        throw new Error(errorDetail || `${res.status} ${res.statusText}`);
      }
      return res.json() as Promise<{ access_token: string; token_type: string }>;
    });
  },

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

  getHistory: () =>
    jsonFetch<{
      history: {
        id: string;
        thread_id: string;
        created_at: string;
        institution_name: string;
        subject: string;
        standard: string;
        difficulty: string;
        chapters: string[];
        objective_count: number;
        subjective_count: number;
        allowed_types: string[];
        paper_pdf: string;
        paper_docx: string;
        answer_pdf: string;
      }[];
    }>("/api/db/history"),

  registerDeviceToken: (payload: { token: string }) =>
    jsonFetch<{ message: string }>("/auth/device-token", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateNotificationSettings: (payload: { notifications_enabled: boolean }) =>
    jsonFetch<{ message: string }>("/auth/notification-settings", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getNotificationSettings: () =>
    jsonFetch<{
      fcm_token: string | null;
      notifications_enabled: boolean;
    }>("/auth/notification-settings"),

  // The backend already returns absolute-relative paths for files, e.g.
  // "/api/download/<thread>/paper.pdf". Just join with the base.
  fileUrl: (apiPath: string) => {
    if (apiPath.startsWith("http")) return apiPath;
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (token) {
      const separator = apiPath.includes("?") ? "&" : "?";
      return `${API_BASE}${apiPath}${separator}token=${encodeURIComponent(token)}`;
    }
    return `${API_BASE}${apiPath}`;
  }
};

