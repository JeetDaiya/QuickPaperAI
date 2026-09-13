import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { SetupPage } from "@/pages/SetupPage";
import { useAuthGuard } from "@/lib/auth";
import { clearToken, isApiError } from "@/lib/api/http";
import { useChapters, useGeneratePaper } from "@/hooks/usePaper";
import { useCurrentUser } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { upsertDraft, setActiveThread } from "@/lib/drafts";

export const Route = createFileRoute("/generate/setup")({
  component: SetupRoute,
});

function SetupRoute() {
  useDocumentTitle("New Exam Paper");
  useAuthGuard();
  const navigate = useNavigate();
  const chaptersQuery = useChapters();
  const currentUserQuery = useCurrentUser();
  const generateMutation = useGeneratePaper();

  // The free-tier quota gate on POST /api/generate raises this with a specific, already-correct
  // reason — append the requested CTA rather than replacing it, so it applies uniformly however
  // that detail text varies (never string-match `.message` to detect this, use `.code`).
  const submitError = generateMutation.error
    ? isApiError(generateMutation.error) && generateMutation.error.code === "PERMISSION_ERROR"
      ? `${generateMutation.error.message} Contact the developer to get access for more generations.`
      : generateMutation.error.message
    : undefined;

  return (
    <SetupPage
      chapters={chaptersQuery.data ?? []}
      userName={currentUserQuery.data?.name}
      userEmail={currentUserQuery.data?.email}
      isSubmitting={generateMutation.isPending}
      isSuperuser={currentUserQuery.data?.is_superuser}
      error={submitError}
      onSubmit={(payload) => {
        generateMutation.mutate(payload, {
          onSuccess: (data) => {
            upsertDraft({
              threadId: data.thread_id,
              institution: payload.institution_name,
              subject: payload.subject,
              standard: payload.standard,
              createdAt: Date.now(),
              status: "Generating",
            });
            setActiveThread(data.thread_id);
            navigate({ to: "/generate/$threadId", params: { threadId: data.thread_id } });
          },
        });
      }}
      onSignOut={() => {
        clearToken();
        navigate({ to: "/login" });
      }}
    />
  );
}
