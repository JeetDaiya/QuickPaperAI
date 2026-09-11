import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
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
  const hasResumed = reconnectKey > 0;
  const { data: status, error, isLoading } = useGenerationStatus(threadId, reconnectKey);
  const cancelMutation = useCancelGeneration();
  const resumeMutation = useResumeGeneration();
  const saveMutation = useSaveToCloud();

  useDocumentTitle(documentTitleFor(status, hasResumed, error));

  useEffect(() => {
    if (status?.status) updateDraftStatus(threadId, draftLabelFor(status.status));
  }, [threadId, status?.status]);

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
    return <ProgressPage paperTitle="New Exam Paper" progress={{}} onCancel={handleCancel} isCancelling={cancelMutation.isPending} />;
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
    return (
      <ReviewPage
        questions={status.questions}
        targets={status.targets}
        isSubmitting={resumeMutation.isPending}
        error={resumeMutation.error?.message}
        onFinalize={(selectedIndices) =>
          resumeMutation.mutate({ threadId, selectedIndices }, { onSuccess: () => setReconnectKey((k) => k + 1) })
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

  // "uninitialized" | "generating" | "failed"
  return (
    <ProgressPage
      paperTitle="New Exam Paper"
      progress={"progress" in status ? status.progress ?? {} : {}}
      onCancel={handleCancel}
      isCancelling={cancelMutation.isPending}
    />
  );
}
