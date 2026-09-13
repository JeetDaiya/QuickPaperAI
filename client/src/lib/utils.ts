import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Natural string sort (so chapter names like "2", "10" order numerically, not lexically). */
export function sortNatural<T>(items: T[], key: (item: T) => string): T[] {
  return [...items].sort((a, b) => key(a).localeCompare(key(b), undefined, { numeric: true, sensitivity: "base" }));
}

/** Mirrors the backend's `first_n_chapter_names` (../QuickPaperAI/src/paper/quota.py) — the
 * free-tier cap is a subject's n lowest-numbered chapters. Chapter names are plain integer
 * strings; the backend assumes this and would itself fail on a non-numeric name, so this does
 * too (no defensive handling for input the backend never produces). */
export function firstNChapterNames(names: string[], n: number): string[] {
  return [...new Set(names)].sort((a, b) => Number(a) - Number(b)).slice(0, n);
}
