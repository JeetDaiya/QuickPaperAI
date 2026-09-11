import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { VerifyOtpPage } from "@/pages/VerifyOtpPage";
import { useSendOtp, useVerifyOtp } from "@/hooks/useAuth";
import { setToken } from "@/lib/api/http";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

type Search = { email: string; purpose: "signup" | "reset_password" };

export const Route = createFileRoute("/verify-otp")({
  validateSearch: (search: Record<string, unknown>): Search => ({
    email: String(search.email ?? ""),
    purpose: search.purpose === "reset_password" ? "reset_password" : "signup",
  }),
  component: VerifyOtpRoute,
});

function VerifyOtpRoute() {
  const { email, purpose } = Route.useSearch();
  const navigate = useNavigate();
  const verifyOtpMutation = useVerifyOtp();
  const sendOtpMutation = useSendOtp();
  const [cooldown, setCooldown] = useState(60);
  const [lockedOut, setLockedOut] = useState(false);
  useDocumentTitle(lockedOut ? "Verification Locked" : "Verify Code");

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  function handleVerify(otp: string) {
    verifyOtpMutation.mutate(
      { email, otp, purpose },
      {
        onSuccess: (data) => {
          if ("access_token" in data) {
            setToken(data.access_token);
            navigate({ to: "/dashboard" });
          } else {
            navigate({ to: "/reset-password", search: { email, token: data.reset_token } });
          }
        },
        onError: (e) => {
          if (e.message.toLowerCase().includes("locked")) setLockedOut(true);
        },
      },
    );
  }

  function handleResend() {
    sendOtpMutation.mutate({ email, purpose }, { onSuccess: () => setCooldown(60) });
  }

  return (
    <VerifyOtpPage
      email={email}
      onChangeEmail={() => navigate({ to: purpose === "signup" ? "/signup" : "/forgot-password" })}
      onVerify={handleVerify}
      onResend={handleResend}
      resendCooldownSeconds={cooldown}
      isSubmitting={verifyOtpMutation.isPending}
      error={verifyOtpMutation.error?.message}
      lockedOut={lockedOut}
    />
  );
}
