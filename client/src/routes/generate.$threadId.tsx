import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { ProgressPage } from "@/pages/ProgressPage";
import { ReviewPage } from "@/pages/ReviewPage";
import { DownloadsPage } from "@/pages/DownloadsPage";
import { useAuthGuard } from "@/lib/auth";
import { useGenerationStatus } from "@/hooks/useGenerationStatus";
import { useCancelGeneration, useResumeGeneration, useSaveToCloud } from "@/hooks/usePaper";
import { resolveFileUrl } from "@/lib/api/http";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { updateDraftStatus, removeDraft, setActiveThread } from "@/lib/drafts";
import type { StatusResponse } from "@/lib/api/types";

export const Route = createFileRoute("/generate/$threadId")({
  component: GenerationRoute,
});

function draftLabelFor(status: string): string {
  if (status === "generating") return "Generating";
  if (status === "awaiting_review") return "Awaiting review";
  if (status === "completed") return "Ready";
  if (status === "failed") return "Failed";
  return status;
}

// The backend has no distinct "compiling" status of its own — after Finalize it goes back to
// "generating" with every chapter already "completed" (compiling only happens once every
// chapter is done). That combination never occurs during the original generation pass either
// (the backend moves straight to "awaiting_review" the moment the last chapter finishes, see
// `get_generation_status` in the backend's service.py), so it's a reliable, backend-derived
// signal — unlike `hasResumed`, it survives a refresh or navigating back into the thread.
function isCompiling(status: StatusResponse): boolean {
  if (status.status !== "generating") return false;
  const chapters = Object.values(status.progress);
  return chapters.length > 0 && chapters.every((c) => c.status === "completed");
}

function documentTitleFor(status: StatusResponse | undefined, hasResumed: boolean, error: Error | null): string {
  if (!status) return "Starting…";
  if (error && status.status !== "completed" && status.status !== "failed") return "Connection Lost";
  if (status.status === "awaiting_review") return hasResumed ? "Compiling Paper…" : "Review Questions";
  if (status.status === "completed") return "Paper Ready";
  if (status.status === "failed") return "Generation Failed";
  if (status.status === "generating") {
    if (isCompiling(status)) return "Compiling Paper…";
    const chapters = Object.values(status.progress);
    const completed = chapters.filter((c) => c.status === "completed").length;
    const pct = chapters.length ? Math.round((completed / chapters.length) * 100) : 0;
    return `Generating… (${pct}%)`;
  }
  return "Starting…";
}

function GenerationRoute() {
  useAuthGuard();
  const { threadId } = Route.useParams();
  const navigate = useNavigate();

  // The backend's own SSE generator ends its HTTP response once status reaches
  // "awaiting_review" (see backend TERMINAL_STATUSES) — our hook closes the connection to
  // match. But that's only a pause, not the end: after the user resumes, the backend keeps
  // working and will eventually push "completed" — to a connection, which needs to exist.
  // Bumping `reconnectKey` forces the hook to open a fresh one right when we resume, instead
  // of leaving the dead connection to be rediscovered only on a manual page refresh.
  const [reconnectKey, setReconnectKey] = useState(0);
  const [hasResumed, setHasResumed] = useState(false);
  const { data: status, error, isLoading } = useGenerationStatus(threadId, reconnectKey, hasResumed);
  const cancelMutation = useCancelGeneration();
  const resumeMutation = useResumeGeneration();
  const saveMutation = useSaveToCloud();

  useDocumentTitle(documentTitleFor(status, hasResumed, error));

  useEffect(() => {
    if (status?.status) updateDraftStatus(threadId, draftLabelFor(status.status));
  }, [threadId, status?.status]);

  // The backend can report "awaiting_review" a moment before the graph checkpoint it reads
  // from actually has the review interrupt's question payload attached (the last chapter's
  // progress update — which wakes this SSE connection's status check — lands slightly before
  // the graph engine hands off to the review node). That race produced an empty question list
  // that only ever fixed itself on a manual refresh. Reconnecting picks up the now-settled
  // checkpoint; capped so a genuinely empty paper doesn't retry forever.
  const emptyReviewRetries = useRef(0);
  useEffect(() => {
    if (hasResumed || status?.status !== "awaiting_review" || status.questions.length > 0) {
      emptyReviewRetries.current = 0;
      return;
    }
    if (emptyReviewRetries.current >= 3) return;
    emptyReviewRetries.current += 1;
    const timer = setTimeout(() => setReconnectKey((k) => k + 1), 1000);
    return () => clearTimeout(timer);
  }, [status, hasResumed]);

  function handleCancel() {
    cancelMutation.mutate(threadId, {
      onSuccess: () => {
        removeDraft(threadId);
        setActiveThread(null);
        navigate({ to: "/dashboard" });
      },
    });
  }

  if (isLoading || !status) {
    return (
      <ProgressPage
        paperTitle="New Exam Paper"
        progress={{}}
        onCancel={handleCancel}
        isCancelling={cancelMutation.isPending}
        onGoHome={() => navigate({ to: "/dashboard" })}
      />
    );
  }

  // Both "completed" and "failed" are terminal — the stream closing itself afterwards isn't
  // an error worth surfacing, since we're not waiting on it for anything further.
  if (error && status.status !== "completed" && status.status !== "failed") {
    return (
      <div className="max-w-xl mx-auto py-24 text-center">
        <p className="font-body-lg text-body-lg text-on-surface-variant mb-4">{error.message}</p>
        <button onClick={() => navigate({ to: "/dashboard" })} className="text-secondary font-label-md text-label-md hover:underline">
          Back to Dashboard
        </button>
      </div>
    );
  }

  if ((status.status === "awaiting_review" && hasResumed) || isCompiling(status)) {
    return (
      <div className="max-w-xl mx-auto py-24 text-center">
        <span className="material-symbols-outlined text-primary text-5xl mb-4 animate-spin">progress_activity</span>
        <h1 className="font-headline-md text-headline-md text-on-surface mb-2">Compiling Your Paper…</h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Your selected questions are being formatted into the final PDF and DOCX. This can take a minute.
        </p>
      </div>
    );
  }

  if (status.status === "awaiting_review") {
    // See the empty-review-retry effect above — while it's still reconnecting to pick up the
    // settled checkpoint, show the loading state instead of a Review screen with no questions.
    if (status.questions.length === 0) {
      return (
        <ProgressPage
          paperTitle="New Exam Paper"
          progress={{}}
          onCancel={handleCancel}
          isCancelling={cancelMutation.isPending}
          onGoHome={() => navigate({ to: "/dashboard" })}
        />
      );
    }
    return (
      <ReviewPage
        questions={status.questions}
        targets={status.targets}
        isSubmitting={resumeMutation.isPending}
        error={resumeMutation.error?.message}
        onFinalize={(selectedIndices) =>
          resumeMutation.mutate(
            { threadId, selectedIndices },
            { onSuccess: () => { setHasResumed(true); setReconnectKey((k) => k + 1); } }
          )
        }
      />
    );
  }

  if (status.status === "completed") {
    return (
      <DownloadsPage
        paperPdfUrl={resolveFileUrl(status.files.paper_pdf)}
        paperDocxUrl={resolveFileUrl(status.files.paper_docx)}
        answerPdfUrl={resolveFileUrl(status.files.answer_pdf)}
        isSaving={saveMutation.isPending}
        saved={saveMutation.isSuccess}
        onSaveToCloud={() => saveMutation.mutate(threadId)}
      />
    );
  }

  if (status.status === "failed") {
    const progress = status.progress ?? {};
    const chapters = Object.values(progress);
    return (
      <main className="w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-12 flex flex-col items-center">
        <div className="text-center mb-12 max-w-2xl w-full">
          <span className="material-symbols-outlined text-error text-5xl mb-4 material-symbols-fill">error</span>
          <h1 className="font-display-lg text-display-lg text-on-surface mb-2">Generation Failed</h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Some chapters could not be generated. You can try again or go back to the dashboard.
          </p>
        </div>

        {status.errors.length > 0 && (
          <div className="w-full max-w-3xl bg-surface border border-error/30 p-6 rounded stamp-shadow mb-8">
            <h2 className="font-headline-md text-headline-md text-on-surface mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-error text-[22px]">warning</span>
              Error Details
            </h2>
            <ul className="space-y-3">
              {status.errors.map((err, i) => (
                <li key={i} className="flex items-start gap-3 p-3 rounded bg-error-container/30 border border-error/20">
                  <span className="font-label-md text-label-md font-semibold text-on-surface shrink-0 mt-0.5">{err.chapter}</span>
                  <span className="font-body-md text-body-md text-on-surface-variant">{err.message}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {chapters.length > 0 && (
          <div className="w-full max-w-3xl bg-surface border border-outline-variant p-6 rounded stamp-shadow mb-8">
            <h2 className="font-headline-md text-headline-md text-on-surface mb-4">Chapter Status</h2>
            <div className="space-y-2">
              {chapters.map((c) => (
                <div key={c.chapter} className="flex items-center justify-between py-2 border-b border-outline-variant last:border-b-0">
                  <span className="font-label-md text-label-md text-on-surface">{c.chapter}</span>
                  <span className={`font-label-sm text-label-sm px-2 py-0.5 rounded-full ${
                    c.status === "failed"
                      ? "bg-error-container text-on-error-container"
                      : c.status === "completed"
                        ? "bg-surface-container-lowest border border-outline text-on-surface"
                        : "bg-surface-container-lowest border border-outline-variant text-on-surface-variant"
                  }`}>
                    {c.status} — {c.generated_count} questions
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-4">
          <button
            onClick={() => navigate({ to: "/dashboard" })}
            className="px-6 py-3 border border-outline-variant text-on-surface-variant hover:text-on-surface font-label-md text-label-md transition-colors duration-200 flex items-center gap-2 rounded-sm bg-surface stamp-shadow"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            Back to Dashboard
          </button>
          <button
            onClick={handleCancel}
            disabled={cancelMutation.isPending}
            className="px-6 py-3 border border-outline-variant text-on-surface-variant hover:text-error hover:border-error hover:bg-error-container font-label-md text-label-md transition-colors duration-200 flex items-center gap-2 rounded-sm bg-surface stamp-shadow disabled:opacity-60"
          >
            <span className="material-symbols-outlined text-[18px]">cancel</span>
            {cancelMutation.isPending ? "Cancelling…" : "Dismiss"}
          </button>
        </div>
      </main>
    );
  }

  // "uninitialized" | "generating"
  return (
    <ProgressPage
      paperTitle="New Exam Paper"
      progress={"progress" in status ? status.progress ?? {} : {}}
      onCancel={handleCancel}
      isCancelling={cancelMutation.isPending}
      onGoHome={() => navigate({ to: "/dashboard" })}
    />
  );
}
