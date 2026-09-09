import type { QueryClient } from "@tanstack/react-query";
import { updateDraftStatus } from "./drafts";
import type { GenerationStatus, StatusResponse } from "./types";

export function statusQueryKey(threadId: string) {
  return ["status", threadId] as const;
}

export function labelForStatus(status: GenerationStatus | string): string {
  if (status === "generating") return "Generating";
  if (status === "awaiting_review") return "Awaiting review";
  if (status === "completed") return "Ready";
  if (status === "failed") return "Failed";
  return status;
}

export function syncStatus(queryClient: QueryClient, threadId: string, data: StatusResponse) {
  queryClient.setQueryData(statusQueryKey(threadId), data);
  try {
    updateDraftStatus(threadId, labelForStatus(data.status));
  } catch (err) {
    console.error("Failed to persist draft status to localStorage:", err);
  }
}
