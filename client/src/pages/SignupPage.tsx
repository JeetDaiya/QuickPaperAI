import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/layout/AuthShell";

export interface SignupPageProps {
  onSubmit: (payload: { name: string; email: string; password: string }) => void;
  isSubmitting: boolean;
  error?: string;
}

export function SignupPage({ onSubmit, isSubmitting, error }: SignupPageProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  return (
    <AuthShell badge="Academic System Clearance: Tier-1 Registration">
      <div className="w-full max-w-[580px] flex flex-col items-center">
      <div className="w-full bg-surface-container-lowest border border-outline-variant p-8 md:p-10 rounded-lg stamp-shadow relative">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-surface-container text-on-surface-variant font-label-sm text-label-sm mb-6 border border-outline-variant/40">
          <span className="w-1.5 h-1.5 rounded-full bg-primary" />
          <span>Tuition &amp; Faculty Portal · New Registration</span>
        </div>

        <div className="mb-8">
          <h1 className="font-headline-md text-headline-md text-on-surface mb-2 tracking-tight">Create Your Account</h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Set up your teaching credentials to access AI paper blueprints, syllabus mappings, and cloud vault.
          </p>
        </div>

        <form
          className="space-y-6"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit({ name, email, password });
          }}
        >
          <div className="flex flex-col">
            <label className="font-label-md text-label-md text-on-surface font-semibold mb-1 flex items-center gap-1.5" htmlFor="name">
              <span className="material-symbols-outlined text-base text-primary">person</span>
              Full Name
            </label>
            <input
              id="name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Dr. Arthur Pendleton"
              className="w-full bg-transparent input-line px-1 py-2 font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface-container-low transition-colors duration-150"
            />
          </div>

          <div className="flex flex-col">
            <label className="font-label-md text-label-md text-on-surface font-semibold mb-1 flex items-center gap-1.5" htmlFor="email">
              <span className="material-symbols-outlined text-base text-primary">school</span>
              Institutional or Work Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="faculty@school.edu"
              className="w-full bg-transparent input-line px-1 py-2 font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface-container-low transition-colors duration-150"
            />
          </div>

          <div className="flex flex-col">
            <label className="font-label-md text-label-md text-on-surface font-semibold mb-1 flex items-center gap-1.5" htmlFor="password">
              <span className="material-symbols-outlined text-base text-primary">lock</span>
              Password
            </label>
            <div className="relative flex items-center">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-transparent input-line px-1 py-2 pr-12 font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant/50 focus:bg-surface-container-low transition-colors duration-150"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-1 text-on-surface-variant hover:text-primary font-label-sm text-label-sm flex items-center gap-1 px-1 py-0.5 rounded transition-colors"
              >
                <span className="material-symbols-outlined text-sm">{showPassword ? "visibility_off" : "visibility"}</span>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <span className="font-label-sm text-label-sm text-outline mt-1.5 flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">info</span>
              8-128 characters
            </span>
          </div>

          {error && (
            <div className="rounded p-3 bg-error-container/60 border border-error/30 flex items-start gap-2.5 text-left" role="alert">
              <span className="material-symbols-outlined text-error shrink-0 text-xl mt-0.5">error</span>
              <p className="font-body-md text-xs leading-normal text-on-error-container opacity-90">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-4 bg-primary-container text-on-primary font-label-md text-label-md py-3 px-6 rounded-lg font-bold shadow hover:bg-primary transition-all duration-200 active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <span>{isSubmitting ? "Creating account…" : "Create Account"}</span>
            <span className="material-symbols-outlined text-base">arrow_forward</span>
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-outline-variant/30 text-center">
          <span className="font-body-md text-body-md text-on-surface-variant">Already have an account?</span>
          <Link to="/login" className="font-label-md text-label-md font-bold text-primary hover:underline ml-1 inline-flex items-center gap-0.5">
            <span>Log in</span>
            <span className="material-symbols-outlined text-sm">north_east</span>
          </Link>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-center gap-2 text-outline font-label-sm text-label-sm">
        <span className="material-symbols-outlined text-sm text-primary">verified_user</span>
        <span>Protected by End-to-End Encryption</span>
      </div>
      </div>
    </AuthShell>
  );
}
