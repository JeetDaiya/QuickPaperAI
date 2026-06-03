const KEY_PREFIX = "qpa.recent_drafts.v1";
const ACTIVE_KEY_PREFIX = "qpa.active_thread";
const MAX = 12;

export interface DraftRecord {
  threadId: string;
  institution: string;
  subject: string;
  standard: string;
  createdAt: number;
  status?: string;
}

function safeStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function getUserSuffix(): string {
  if (typeof window === "undefined") return "";
  const token = localStorage.getItem("token");
  if (!token) return "";
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return "";
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      window.atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    const payload = JSON.parse(jsonPayload);
    return payload.sub ? `:${payload.sub}` : "";
  } catch (e) {
    console.error("Failed to decode token for drafts prefix:", e);
    return "";
  }
}

function getKeys() {
  const suffix = getUserSuffix();
  return {
    KEY: `${KEY_PREFIX}${suffix}`,
    ACTIVE_KEY: `${ACTIVE_KEY_PREFIX}${suffix}`,
  };
}

export function loadDrafts(): DraftRecord[] {
  const s = safeStorage();
  if (!s) return [];
  try {
    const { KEY } = getKeys();
    const raw = s.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as DraftRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function upsertDraft(record: DraftRecord) {
  const s = safeStorage();
  if (!s) return;
  const { KEY } = getKeys();
  const drafts = loadDrafts().filter((d) => d.threadId !== record.threadId);
  drafts.unshift(record);
  s.setItem(KEY, JSON.stringify(drafts.slice(0, MAX)));
}

export function updateDraftStatus(threadId: string, status: string) {
  const s = safeStorage();
  if (!s) return;
  const { KEY } = getKeys();
  const drafts = loadDrafts();
  const idx = drafts.findIndex((d) => d.threadId === threadId);
  if (idx === -1) return;
  drafts[idx] = { ...drafts[idx], status };
  s.setItem(KEY, JSON.stringify(drafts));
}

export function removeDraft(threadId: string) {
  const s = safeStorage();
  if (!s) return;
  const { KEY } = getKeys();
  const drafts = loadDrafts().filter((d) => d.threadId !== threadId);
  s.setItem(KEY, JSON.stringify(drafts));
}

export function setActiveThread(threadId: string | null) {
  const s = safeStorage();
  if (!s) return;
  const { ACTIVE_KEY } = getKeys();
  if (threadId) s.setItem(ACTIVE_KEY, threadId);
  else s.removeItem(ACTIVE_KEY);
}

export function getActiveThread(): string | null {
  const s = safeStorage();
  if (!s) return null;
  const { ACTIVE_KEY } = getKeys();
  return s.getItem(ACTIVE_KEY);
}
