import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { DeskHeader } from "@/components/desk-header";
import { api } from "@/lib/api";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { Eye, EyeOff } from "lucide-react";

export const Route = createFileRoute("/verify-otp")({
  validateSearch: (search: Record<string, unknown>) => {
    return {
      email: (search.email as string) || "",
      purpose: (search.purpose as "signup" | "reset_password") || "signup",
    };
  },
  head: () => ({
    meta: [
      { title: "Verify Code — QuickPaperAI" },
      {
        name: "description",
        content: "Enter your 6-digit verification code to activate your account or reset your password.",
      },
    ],
  }),
  component: VerifyOtpPage,
});

function VerifyOtpPage() {
  const navigate = useNavigate();
  const { email: initialEmail, purpose } = Route.useSearch();
  const [email, setEmail] = useState(initialEmail);
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(60);
  const [isLockedOut, setIsLockedOut] = useState(false);

  const isResetMode = purpose === "reset_password";

  // 60 second countdown timer for resend OTP
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  async function handleResendOtp() {
    if (cooldown > 0 || resending || isLockedOut) return;
    setError(null);
    setResendSuccess(null);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      return setError("Email address is required to send verification code.");
    }

    setResending(true);
    try {
      await api.sendOtp({ email: cleanEmail, purpose });
      setCooldown(60);
      setResendSuccess("A new 6-digit code has been sent to your email.");
    } catch (err: any) {
      const msg = err.message || "";
      if (msg.toLowerCase().includes("too many") || msg.includes("locked") || msg.includes("15 minutes")) {
        setIsLockedOut(true);
        setError("Too many verification attempts. Account locked for 15 minutes.");
      } else if (msg.includes("60 seconds") || msg.includes("wait")) {
        setError("Please wait 60 seconds before requesting another code.");
      } else {
        setError(msg || "Failed to resend verification code.");
      }
    } finally {
      setResending(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResendSuccess(null);
    setSuccess(false);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      return setError("Email address is required.");
    }
    if (!otp || otp.length < 6) {
      return setError("Please enter the complete 6-digit verification code.");
    }
    if (isResetMode && (!newPassword || newPassword.length < 6)) {
      return setError("New password must be at least 6 characters.");
    }

    setSubmitting(true);
    try {
      if (isResetMode) {
        // 1. Verify OTP for password reset
        const res = await api.verifyOtp({ email: cleanEmail, otp, purpose: "reset_password" });
        if (!res.reset_token) {
          throw new Error("Failed to obtain password reset authorization token.");
        }
        // 2. Execute password reset
        await api.resetPassword({
          email: cleanEmail,
          token: res.reset_token,
          new_password: newPassword,
        });

        setSuccess(true);
        setTimeout(() => {
          navigate({ to: "/login", search: { message: "password_reset" } });
        }, 1000);
      } else {
        // Signup verification flow
        const res = await api.verifyOtp({ email: cleanEmail, otp, purpose: "signup" });
        if (res.access_token) {
          localStorage.setItem("token", res.access_token);
        }
        setSuccess(true);
        setTimeout(() => {
          navigate({ to: "/" });
        }, 800);
      }
    } catch (err: any) {
      const msg = err.message || "";
      if (msg.toLowerCase().includes("too many") || msg.includes("locked") || msg.includes("15 minutes")) {
        setIsLockedOut(true);
        setError("Too many verification attempts. Please try again after 15 minutes.");
      } else if (msg.toLowerCase().includes("not found") || msg.toLowerCase().includes("expired")) {
        setError("Verification code expired or not found. Please request a new code.");
      } else if (msg.toLowerCase().includes("invalid") || msg.toLowerCase().includes("incorrect")) {
        setError("Incorrect 6-digit verification code. Please check your email and try again.");
      } else {
        setError(msg || "Verification failed. Please check the code and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen surface-paper flex flex-col">
      <DeskHeader hideNav />

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md animate-shuffle">
          {/* Card simulating an examiner's notebook page */}
          <div className="relative border border-[var(--paper-rule)] bg-[var(--card)] p-8 sm:p-10 stamp-shadow">
            {/* Perforated edge effect on the left side of the card */}
            <div className="absolute left-0 top-0 bottom-0 w-1 perforated-left opacity-30" />

            <div className="mb-8">
              <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--graphite)]">
                {isResetMode ? "Logbook — Auth 04" : "Logbook — Auth 03"}
              </p>
              <h1 className="mt-3 font-serif text-4xl leading-tight">
                {isResetMode ? (
                  <>Set new <span className="italic">Password</span>.</>
                ) : (
                  <>Verify your <span className="italic">Identity</span>.</>
                )}
              </h1>
              <p className="mt-2 text-sm text-[var(--graphite)]">
                {isResetMode
                  ? "Enter the 6-digit reset code sent to your email and your new password."
                  : "Enter the 6-digit verification code sent to your email address."}
              </p>
            </div>

            {error && (
              <div className="mb-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)] animate-shake">
                <span className="font-bold mr-1">⚠ Error:</span> {error}
              </div>
            )}

            {resendSuccess && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Sent:</span> {resendSuccess}
              </div>
            )}

            {success && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Success:</span>{" "}
                {isResetMode
                  ? "Password reset successfully! Redirecting to Sign In..."
                  : "Email verified successfully! Redirecting to Examiner's Desk..."}
              </div>
            )}

            <form onSubmit={onSubmit} className="space-y-6">
              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] mb-2">
                  01 · Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="examiner@school.com"
                  className="w-full border-b border-[var(--paper-rule)] bg-transparent pb-2 font-serif text-xl outline-none focus:border-[var(--vermillion)] transition-colors"
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] mb-2">
                  02 · 6-Digit Passcode
                </label>
                <div className="flex justify-center pt-2 pb-1">
                  <InputOTP
                    maxLength={6}
                    value={otp}
                    onChange={(val) => setOtp(val)}
                  >
                    <InputOTPGroup className="gap-2">
                      <InputOTPSlot index={0} className="w-11 h-12 text-xl font-mono border-[var(--paper-rule)] focus:border-[var(--vermillion)]" />
                      <InputOTPSlot index={1} className="w-11 h-12 text-xl font-mono border-[var(--paper-rule)] focus:border-[var(--vermillion)]" />
                      <InputOTPSlot index={2} className="w-11 h-12 text-xl font-mono border-[var(--paper-rule)] focus:border-[var(--vermillion)]" />
                      <InputOTPSlot index={3} className="w-11 h-12 text-xl font-mono border-[var(--paper-rule)] focus:border-[var(--vermillion)]" />
                      <InputOTPSlot index={4} className="w-11 h-12 text-xl font-mono border-[var(--paper-rule)] focus:border-[var(--vermillion)]" />
                      <InputOTPSlot index={5} className="w-11 h-12 text-xl font-mono border-[var(--paper-rule)] focus:border-[var(--vermillion)]" />
                    </InputOTPGroup>
                  </InputOTP>
                </div>
              </div>

              {isResetMode && (
                <div>
                  <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] mb-2">
                    03 · New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full border-b border-[var(--paper-rule)] bg-transparent pb-2 pr-10 font-mono text-lg outline-none focus:border-[var(--vermillion)] transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-0 top-1/2 -translate-y-1/2 text-[var(--graphite)] hover:text-[var(--vermillion)] focus:outline-none"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              )}

              {isLockedOut ? (
                <div className="pt-2 font-mono text-xs text-[var(--vermillion)] flex items-center gap-2">
                  <span>🔒</span>
                  <span>Account locked for 15 minutes due to multiple failed attempts.</span>
                </div>
              ) : (
                <div className="pt-2 flex items-center justify-between font-mono text-xs">
                  <span className="text-[var(--graphite)]">Didn't receive code?</span>
                  <button
                    type="button"
                    onClick={handleResendOtp}
                    disabled={cooldown > 0 || resending}
                    className="text-[var(--graphite)] hover:text-[var(--vermillion)] disabled:opacity-50 underline-hand transition-colors"
                  >
                    {resending
                      ? "Sending..."
                      : cooldown > 0
                      ? `Resend code (${cooldown}s)`
                      : "Resend Code"}
                  </button>
                </div>
              )}

              <div className="pt-4 flex items-center justify-between border-t border-[var(--paper-rule)]">
                <Link
                  to="/login"
                  className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--graphite)] hover:text-[var(--vermillion)] hover:underline-hand pb-0.5 transition-colors"
                >
                  Back to Sign In
                </Link>
                <button
                  type="submit"
                  disabled={submitting || success || isLockedOut}
                  className="group inline-flex items-center gap-3 rounded-sm bg-[var(--ink)] px-6 py-3 font-mono text-xs uppercase tracking-[0.22em] text-[var(--ink-foreground)] transition hover:bg-[var(--vermillion)] disabled:opacity-50"
                >
                  <span
                    aria-hidden
                    className="inline-block h-2 w-2 rounded-full bg-[var(--vermillion-soft)] group-hover:bg-[var(--paper)]"
                  />
                  {submitting
                    ? isResetMode
                      ? "Resetting…"
                      : "Verifying…"
                    : isResetMode
                    ? "Reset Password"
                    : "Verify Code"}
                  <span aria-hidden className="opacity-60 group-hover:translate-x-1 transition">
                    →
                  </span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
