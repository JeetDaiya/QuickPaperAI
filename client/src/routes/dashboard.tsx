import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DashboardPage } from "@/pages/DashboardPage";
import { useAuthGuard } from "@/lib/auth";
import { clearToken } from "@/lib/api/http";
import { useHistory, useNotificationSettings } from "@/hooks/usePaper";
import { useUpdateNotificationSettings } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { loadDrafts, type DraftRecord } from "@/lib/drafts";

export const Route = createFileRoute("/dashboard")({
  component: DashboardRoute,
});

function DashboardRoute() {
  useDocumentTitle("Dashboard");
  useAuthGuard();
  const navigate = useNavigate();
  const historyQuery = useHistory();
  const notificationSettingsQuery = useNotificationSettings();
  const updateNotifications = useUpdateNotificationSettings();
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);

  useEffect(() => {
    setDrafts(loadDrafts());
  }, []);

  return (
    <DashboardPage
      history={historyQuery.data ?? []}
      drafts={drafts}
      notificationsEnabled={notificationSettingsQuery.data?.notifications_enabled ?? true}
      onToggleNotifications={(enabled) => updateNotifications.mutate({ notifications_enabled: enabled })}
      onSignOut={() => {
        clearToken();
        navigate({ to: "/login" });
      }}
    />
  );
}
