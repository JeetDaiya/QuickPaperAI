import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { SignupPage } from "@/pages/SignupPage";
import { useRegister, useSendOtp } from "@/hooks/useAuth";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export const Route = createFileRoute("/signup")({
  component: SignupRoute,
});

function SignupRoute() {
  useDocumentTitle("Sign Up");
  const navigate = useNavigate();
  const registerMutation = useRegister();
  const sendOtpMutation = useSendOtp();
  const [error, setError] = useState<string>();

  async function handleSubmit(payload: { name: string; email: string; password: string }) {
    setError(undefined);
    try {
      await registerMutation.mutateAsync(payload);
      await sendOtpMutation.mutateAsync({ email: payload.email, purpose: "signup" });
      navigate({ to: "/verify-otp", search: { email: payload.email, purpose: "signup" } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed.");
    }
  }

  return (
    <SignupPage
      onSubmit={handleSubmit}
      isSubmitting={registerMutation.isPending || sendOtpMutation.isPending}
      error={error}
    />
  );
}
