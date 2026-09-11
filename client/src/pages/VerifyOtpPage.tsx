import { useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/layout/AuthShell";

export interface VerifyOtpPageProps {
  email: string;
  onChangeEmail: () => void;
  onVerify: (otp: string) => void;
  onResend: () => void;
  resendCooldownSeconds: number;
  isSubmitting: boolean;
  error?: string;
  lockedOut?: boolean;
}

const DIGIT_COUNT = 6;

export function VerifyOtpPage({
  email,
  onChangeEmail,
  onVerify,
  onResend,
  resendCooldownSeconds,
  isSubmitting,
  error,
  lockedOut,
}: VerifyOtpPageProps) {
  const [digits, setDigits] = useState<string[]>(Array(DIGIT_COUNT).fill(""));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  function setDigit(index: number, value: string) {
    const char = value.replace(/\D/g, "").slice(-1);
    setDigits((prev) => {
      const next = [...prev];
      next[index] = char;
      return next;
    });
    if (char && index < DIGIT_COUNT - 1) inputRefs.current[index + 1]?.focus();
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Backspace" && !digits[index] && index > 0) inputRefs.current[index - 1]?.focus();
  }

  const code = digits.join("");

  return (
    <AuthShell badge="Academic System Clearance: Tier-1 Verification">
      <div className="w-full max-w-[560px]">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 sm:p-10 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-primary-container to-secondary" />

          <div className="flex flex-wrap items-center justify-between gap-2 pb-4 mb-6 border-b border-dashed border-outline-variant">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container text-primary font-label-sm text-label-sm font-semibold">
              <span className="material-symbols-outlined text-[15px]">verified_user</span>
              <span>Identity Verification</span>
            </div>
          </div>

          <div className="space-y-2 mb-6">
            <h1 className="font-headline-md text-headline-md text-on-surface tracking-tight">Check your email</h1>
            <p className="font-body-md text-body-md text-on-surface-variant">
              We sent a 6-digit verification code to{" "}
              <span className="font-label-md text-label-md font-semibold text-on-surface">{email}</span>.{" "}
              <button type="button" onClick={onChangeEmail} className="inline-flex items-center text-secondary font-label-sm text-label-sm hover:underline">
                (Change email)
              </button>
            </p>
          </div>

          {error && (
            <div className="mb-6 p-3.5 rounded-lg bg-surface-container-high border border-outline-variant flex items-start gap-3">
              <span className="material-symbols-outlined text-primary text-[20px] shrink-0 mt-0.5">error</span>
              <p className="font-label-md text-label-sm font-semibold text-primary">{error}</p>
            </div>
          )}

          <form
            className="space-y-6"
            onSubmit={(e) => {
              e.preventDefault();
              onVerify(code);
            }}
          >
            <div>
              <label className="block font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant mb-3">
                One-Time Code (6 Digits)
              </label>
              <div className="grid grid-cols-6 gap-2 sm:gap-3">
                {digits.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => {
                      inputRefs.current[i] = el;
                    }}
                    aria-label={`Digit ${i + 1}`}
                    className="w-full aspect-square sm:h-14 text-center font-label-md text-xl font-mono font-bold bg-surface-container-low text-on-surface border border-outline-variant rounded focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-all"
                    maxLength={1}
                    inputMode="numeric"
                    placeholder="·"
                    value={digit}
                    onChange={(e) => setDigit(i, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(i, e)}
                  />
                ))}
              </div>
            </div>

            {lockedOut && (
              <div className="px-3.5 py-2.5 rounded bg-surface-container-low border-l-2 border-outline flex items-center gap-2.5">
                <span className="material-symbols-outlined text-outline text-[18px] shrink-0">shield</span>
                <p className="font-label-sm text-label-sm text-on-surface-variant">
                  <span className="font-semibold text-on-surface">Account locked:</span> too many failed attempts. Try again in 15 minutes.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || code.length !== DIGIT_COUNT || lockedOut}
              className="w-full py-3 px-4 rounded bg-primary text-on-primary font-label-md text-label-md font-semibold tracking-wide flex items-center justify-center gap-2 shadow-sm hover:bg-primary-container active:scale-[0.99] transition-all duration-150 disabled:opacity-60"
            >
              <span>{isSubmitting ? "Verifying…" : "Verify Code"}</span>
              <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
            </button>

            <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left font-label-sm text-label-sm">
              <div className="flex items-center gap-1.5 text-on-surface-variant">
                <span className="material-symbols-outlined text-[16px] text-outline">schedule</span>
                {resendCooldownSeconds > 0 ? (
                  <span>
                    Didn't receive the code? <span className="font-mono font-semibold text-on-surface">Resend in {resendCooldownSeconds}s</span>
                  </span>
                ) : (
                  <span>Didn't receive the code?</span>
                )}
              </div>
              <button
                type="button"
                onClick={onResend}
                disabled={resendCooldownSeconds > 0}
                className="text-secondary hover:text-primary transition-colors duration-150 disabled:opacity-50 disabled:text-outline font-semibold"
              >
                Resend now
              </button>
            </div>

            <div className="space-y-3 pt-1 text-center border-t border-dashed border-outline-variant pt-4">
              <Link to="/login" className="inline-flex items-center gap-1.5 font-label-sm text-label-sm font-semibold text-secondary hover:underline">
                <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                <span>Back to Sign In</span>
              </Link>
            </div>
          </form>
        </div>
      </div>
    </AuthShell>
  );
}
