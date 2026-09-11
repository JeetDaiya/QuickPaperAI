import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { ResetPasswordPage } from "@/pages/ResetPasswordPage";
import { useResetPassword } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

type Search = { email: string; token: string };

export const Route = createFileRoute("/reset-password")({
  validateSearch: (search: Record<string, unknown>): Search => ({
    email: String(search.email ?? ""),
    token: String(search.token ?? ""),
  }),
  component: ResetPasswordRoute,
});

function ResetPasswordRoute() {
  const { email, token } = Route.useSearch();
  const resetPasswordMutation = useResetPassword();
  const [success, setSuccess] = useState(false);
  useDocumentTitle(success ? "Password Updated" : "Set New Password");

  function handleSubmit(newPassword: string) {
    resetPasswordMutation.mutate(
      { email, token, new_password: newPassword },
      { onSuccess: () => setSuccess(true) },
    );
  }

  return (
    <ResetPasswordPage
      onSubmit={handleSubmit}
      isSubmitting={resetPasswordMutation.isPending}
      error={resetPasswordMutation.error?.message}
      success={success}
    />
  );
}
