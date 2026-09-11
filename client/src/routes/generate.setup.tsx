import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { SetupPage } from "@/pages/SetupPage";
import { useAuthGuard } from "@/lib/auth";
import { clearToken } from "@/lib/api/http";
import { useChapters, useGeneratePaper } from "@/hooks/usePaper";
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
  const generateMutation = useGeneratePaper();

  return (
    <SetupPage
      chapters={chaptersQuery.data ?? []}
      isSubmitting={generateMutation.isPending}
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
