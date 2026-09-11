import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/layout/AuthShell";

export interface ResetPasswordPageProps {
  onSubmit: (newPassword: string) => void;
  isSubmitting: boolean;
  error?: string;
  success: boolean;
}

export function ResetPasswordPage({ onSubmit, isSubmitting, error, success }: ResetPasswordPageProps) {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const mismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;

  return (
    <AuthShell badge="Academic System Clearance: Tier-1 Credential Update">
      <div className="w-full max-w-[580px]">
        <div className="bg-surface-container-lowest rounded-lg border-2 border-outline-variant/80 p-8 md:p-10 relative">
          <div className="flex items-center gap-2 mb-4">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded bg-surface-container border border-outline-variant text-primary font-label-sm text-label-sm font-bold tracking-wide uppercase">
              <span className="material-symbols-outlined text-[14px]">verified_user</span>
              Credential Update
            </span>
          </div>

          {!success ? (
            <>
              <div className="mb-7">
                <h1 className="font-headline-md text-headline-md text-on-surface font-bold tracking-tight mb-2">Set a new password</h1>
                <p className="font-body-md text-body-md text-on-surface-variant leading-relaxed">
                  Your identity has been verified. Please set a new password for your account.
                </p>
              </div>

              <div className="w-full border-t border-dashed border-outline-variant mb-7" />

              <form
                className="space-y-6"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!mismatch) onSubmit(newPassword);
                }}
              >
                <div>
                  <label className="font-label-md text-label-md font-semibold text-on-surface flex items-center gap-1.5 mb-1.5" htmlFor="new-password">
                    <span className="material-symbols-outlined text-outline text-[18px]">lock</span>
                    New Password
                  </label>
                  <div className="relative flex items-center">
                    <input
                      id="new-password"
                      type={showPassword ? "text" : "password"}
                      required
                      minLength={8}
                      maxLength={128}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••••••••••"
                      className="w-full bg-surface-container-low px-3.5 py-2.5 text-on-surface font-label-md text-label-md border-0 border-b-2 border-outline-variant rounded-t transition-colors placeholder:text-outline/60 focus:outline-none focus:border-secondary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 text-outline hover:text-on-surface transition-colors p-1"
                    >
                      <span className="material-symbols-outlined text-[20px]">{showPassword ? "visibility_off" : "visibility"}</span>
                    </button>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="font-label-md text-label-md font-semibold text-on-surface flex items-center gap-1.5" htmlFor="confirm-password">
                      <span className="material-symbols-outlined text-outline text-[18px]">lock_reset</span>
                      Confirm New Password
                    </label>
                    {confirmPassword.length > 0 && !mismatch && (
                      <span className="font-label-sm text-label-sm text-tertiary flex items-center gap-1 font-semibold">
                        <span className="material-symbols-outlined text-[16px] text-tertiary">check_circle</span>
                        Match confirmed
                      </span>
                    )}
                  </div>
                  <input
                    id="confirm-password"
                    type={showPassword ? "text" : "password"}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••••••"
                    className="w-full bg-surface-container-low px-3.5 py-2.5 text-on-surface font-label-md text-label-md border-0 border-b-2 border-outline-variant rounded-t transition-colors placeholder:text-outline/60 focus:outline-none focus:border-secondary"
                  />
                  {mismatch && <p className="font-label-sm text-label-sm text-error mt-1.5">Passwords don't match.</p>}
                </div>

                <div className="flex items-start gap-2 bg-surface-container-low p-3 rounded border border-outline-variant/60">
                  <span className="material-symbols-outlined text-outline text-[18px] mt-0.5">info</span>
                  <p className="font-label-sm text-label-sm text-on-surface-variant leading-tight">
                    <strong>Password Policy:</strong> 8-128 characters.
                  </p>
                </div>

                {error && <p className="font-label-sm text-label-sm text-error">{error}</p>}

                <button
                  type="submit"
                  disabled={isSubmitting || mismatch || !newPassword}
                  className="w-full py-3.5 px-6 rounded bg-primary-container hover:bg-primary active:scale-[0.99] text-on-primary-container transition-all duration-200 flex items-center justify-center gap-2 shadow-sm font-label-md text-label-md font-bold disabled:opacity-60"
                >
                  <span>{isSubmitting ? "Resetting…" : "Reset Password"}</span>
                  <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                </button>
              </form>
            </>
          ) : (
            <div className="space-y-6">
              <div className="p-6 rounded-lg bg-surface-container-low border-2 border-secondary/40 relative overflow-hidden">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full bg-secondary-fixed text-secondary flex items-center justify-center shrink-0 shadow-sm border border-secondary/20">
                    <span className="material-symbols-outlined text-[28px] material-symbols-fill">task_alt</span>
                  </div>
                  <div className="space-y-1.5">
                    <h2 className="font-headline-md text-[22px] text-on-surface font-bold leading-tight">Password successfully updated!</h2>
                    <p className="font-body-md text-body-md text-on-surface-variant">
                      Your credentials have been updated. Previous session tokens have been revoked.
                    </p>
                  </div>
                </div>
              </div>
              <Link
                to="/login"
                className="w-full py-3.5 px-6 rounded bg-secondary text-on-secondary active:scale-[0.99] transition-all flex items-center justify-center gap-2 shadow-sm font-label-md text-label-md font-bold"
              >
                <span>Proceed to Log In</span>
                <span className="material-symbols-outlined text-[20px]">arrow_right_alt</span>
              </Link>
            </div>
          )}

          <div className="w-full border-t border-dashed border-outline-variant mt-8 pt-4">
            <div className="flex items-center justify-center gap-2 text-center text-outline">
              <span className="material-symbols-outlined text-[16px]">verified</span>
              <span className="font-label-sm text-label-sm tracking-wide">Protected by End-to-End Encryption</span>
            </div>
          </div>
        </div>
      </div>
    </AuthShell>
  );
}
