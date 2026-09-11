import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ForgotPasswordPage } from "@/pages/ForgotPasswordPage";
import { useSendOtp } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export const Route = createFileRoute("/forgot-password")({
  component: ForgotPasswordRoute,
});

function ForgotPasswordRoute() {
  useDocumentTitle("Reset Password");
  const navigate = useNavigate();
  const sendOtpMutation = useSendOtp();

  function handleSubmit(email: string) {
    sendOtpMutation.mutate(
      { email, purpose: "reset_password" },
      { onSuccess: () => navigate({ to: "/verify-otp", search: { email, purpose: "reset_password" } }) },
    );
  }

  return <ForgotPasswordPage onSubmit={handleSubmit} isSubmitting={sendOtpMutation.isPending} />;
}
