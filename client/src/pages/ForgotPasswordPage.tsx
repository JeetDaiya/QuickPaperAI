import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/layout/AuthShell";

export interface ForgotPasswordPageProps {
  onSubmit: (email: string) => void;
  isSubmitting: boolean;
}

/** Entry point for the reset-password flow — not in the original wireframe set, but required
 * by the real contract: /auth/reset-password needs a reset_token that only exists after
 * requesting + verifying an OTP for a known email. Matches the AuthShell/card pattern of the
 * other four auth screens. */
export function ForgotPasswordPage({ onSubmit, isSubmitting }: ForgotPasswordPageProps) {
  const [email, setEmail] = useState("");

  return (
    <AuthShell badge="Academic System Clearance: Tier-1">
      <div className="w-full max-w-[520px] bg-surface-container-lowest border border-outline-variant rounded stamp-shadow p-8 md:p-10">
        <div className="text-center mb-8">
          <h2 className="font-headline-md text-headline-md-mobile md:text-headline-md text-on-surface mb-1">
            Reset your password
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Enter your account email and we'll send you a verification code.
          </p>
        </div>

        <div className="perforated-divider mb-6" />

        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(email);
          }}
        >
          <div className="space-y-1.5 text-left">
            <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="email">
              Institutional or Work Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="faculty@yourschool.edu"
              className="w-full py-2.5 input-line border-b-2 text-on-surface font-label-md text-label-md focus:bg-surface-container-low focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-6 bg-primary-container text-on-primary rounded font-label-md text-label-md font-bold hover:bg-primary transition-all duration-200 flex items-center justify-center gap-2 shadow-sm disabled:opacity-60"
          >
            <span>{isSubmitting ? "Sending…" : "Send Verification Code"}</span>
            <span className="material-symbols-outlined text-lg">arrow_forward</span>
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-outline-variant text-center">
          <Link to="/login" className="font-label-md text-label-md text-secondary hover:underline">
            Back to Sign In
          </Link>
        </div>
      </div>
    </AuthShell>
  );
}
