// Recent-drafts persistence in localStorage. UUIDs never surface to the
// teacher — only friendly labels (institution · subject · class · date).

const KEY = "qpa.recent_drafts.v1";
const ACTIVE_KEY = "qpa.active_thread";
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

export function loadDrafts(): DraftRecord[] {
  const s = safeStorage();
  if (!s) return [];
  try {
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
  const drafts = loadDrafts().filter((d) => d.threadId !== record.threadId);
  drafts.unshift(record);
  s.setItem(KEY, JSON.stringify(drafts.slice(0, MAX)));
}

export function updateDraftStatus(threadId: string, status: string) {
  const s = safeStorage();
  if (!s) return;
  const drafts = loadDrafts();
  const idx = drafts.findIndex((d) => d.threadId === threadId);
  if (idx === -1) return;
  drafts[idx] = { ...drafts[idx], status };
  s.setItem(KEY, JSON.stringify(drafts));
}

export function removeDraft(threadId: string) {
  const s = safeStorage();
  if (!s) return;
  const drafts = loadDrafts().filter((d) => d.threadId !== threadId);
  s.setItem(KEY, JSON.stringify(drafts));
}

export function setActiveThread(threadId: string | null) {
  const s = safeStorage();
  if (!s) return;
  if (threadId) s.setItem(ACTIVE_KEY, threadId);
  else s.removeItem(ACTIVE_KEY);
}

export function getActiveThread(): string | null {
  const s = safeStorage();
  if (!s) return null;
  return s.getItem(ACTIVE_KEY);
}
