import { useEffect } from "react";

/** Sets the browser tab title to "<title> · QuickPaperAI" (or just "QuickPaperAI" if omitted),
 * restoring the previous title on unmount so navigating away doesn't leave a stale one behind. */
export function useDocumentTitle(title?: string) {
  useEffect(() => {
    const previous = document.title;
    document.title = title ? `${title} · QuickPaperAI` : "QuickPaperAI";
    return () => {
      document.title = previous;
    };
  }, [title]);
}
