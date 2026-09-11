import { useEffect, useRef, useState } from "react";
import { statusStreamUrl } from "@/lib/api/paper";
import type { StatusResponse } from "@/lib/api/types";

export interface UseGenerationStatusReturn {
  data: StatusResponse | undefined;
  error: Error | null;
  isLoading: boolean;
  isStreaming: boolean;
}

// Matches the backend's own TERMINAL_STATUSES (routes.py) — the point at which its SSE
// generator ends that HTTP response itself. "awaiting_review" is only a pause, not a stop:
// after the caller resumes generation, the backend keeps working and will eventually push
// "completed" — but only to a connection that's still open. See `reconnectKey` below.
const isTerminal = (s?: string) => s === "completed" || s === "failed" || s === "awaiting_review";

export function useGenerationStatus(threadId: string, reconnectKey: number = 0): UseGenerationStatusReturn {
  const [data, setData] = useState<StatusResponse | undefined>(undefined);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!threadId) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    const es = new EventSource(statusStreamUrl(threadId));
    eventSourceRef.current = es;

    es.onopen = () => {
      if (isMounted) {
        setIsStreaming(true);
        setIsLoading(false);
        setError(null);
      }
    };

    es.onmessage = (event) => {
      if (!isMounted) return;
      try {
        const parsed: StatusResponse = JSON.parse(event.data);
        setData(parsed);
        setIsLoading(false);
        setError(null);
        if (isTerminal(parsed.status)) {
          setIsStreaming(false);
          es.close();
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error("Invalid SSE payload"));
      }
    };

    // The browser's EventSource auto-retries on a transient error (network blip, proxy
    // timeout) as long as we don't call close() — closing here would silently kill the
    // connection and leave the UI stuck until a manual refresh. Only readyState === CLOSED
    // means the browser itself gave up (e.g. the server returned a non-retryable status like
    // 401/403/404 on reconnect) — that's the only case worth surfacing as a real error.
    es.onerror = () => {
      if (!isMounted) return;
      setIsStreaming(false);
      if (es.readyState === EventSource.CLOSED) {
        setIsLoading(false);
        setError(new Error("Progress stream connection ended."));
      }
    };

    return () => {
      isMounted = false;
      es.close();
      eventSourceRef.current = null;
    };
    // `reconnectKey` is a deliberate re-trigger: bump it after a successful resume so a fresh
    // connection opens even though `threadId` hasn't changed and the previous one already
    // closed itself on "awaiting_review".
  }, [threadId, reconnectKey]);

  return {
    data,
    error,
    isLoading,
    isStreaming: isStreaming && !isTerminal(data?.status),
  };
}
