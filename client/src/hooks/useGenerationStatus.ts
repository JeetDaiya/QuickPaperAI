import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import type { StatusResponse } from "@/lib/types";

export interface UseGenerationStatusReturn {
  data: StatusResponse | undefined;
  error: Error | null;
  isLoading: boolean;
  isStreaming: boolean;
}

export function useGenerationStatus(threadId: string): UseGenerationStatusReturn {
  const [data, setData] = useState<StatusResponse | undefined>(undefined);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Terminal statuses that should stop streaming
  const isTerminal = (s?: string) =>
    s === "completed" || s === "failed" || s === "awaiting_review";

  useEffect(() => {
    if (!threadId || typeof window === "undefined") return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    try {
      const streamUrl = api.statusStreamUrl(threadId);
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        if (isMounted) {
          setIsStreaming(true);
          setIsLoading(false);
        }
      };

      es.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const parsed: StatusResponse = JSON.parse(event.data);
          setData(parsed);
          setIsLoading(false);

          if (isTerminal(parsed.status)) {
            setIsStreaming(false);
            es.close();
          }
        } catch (err) {
          console.error("Failed to parse SSE JSON payload:", err);
          if (isMounted) {
            setError(err instanceof Error ? err : new Error("Invalid SSE payload"));
          }
        }
      };

      es.onerror = (err) => {
        if (isMounted) {
          setIsStreaming(false);
          setIsLoading(false);
          // If we haven't received terminal state, report stream connection closed
          if (!data || !isTerminal(data.status)) {
            setError(new Error("Progress stream connection ended."));
          }
        }
        es.close();
      };
    } catch (e) {
      console.error("Failed to initialize EventSource:", e);
      if (isMounted) {
        setError(e instanceof Error ? e : new Error("Failed to start status stream"));
        setIsLoading(false);
        setIsStreaming(false);
      }
    }

    return () => {
      isMounted = false;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [threadId]);

  return {
    data,
    error,
    isLoading,
    isStreaming: isStreaming && !isTerminal(data?.status),
  };
}
