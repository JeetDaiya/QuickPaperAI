import { jsonFetch } from "./http";
import type { ChapterInfo, PaperHistory } from "./types";

export function getChapters() {
  return jsonFetch<{ chapters: ChapterInfo[] }>("/api/db/get-chapters");
}

export function getHistory() {
  return jsonFetch<{ history: PaperHistory[] }>("/api/db/history");
}
