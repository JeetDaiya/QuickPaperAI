import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { AuthShell } from "@/components/layout/AuthShell";

export interface LoginPageProps {
  onSubmit: (email: string, password: string) => void;
  isSubmitting: boolean;
  error?: string;
}

export function LoginPage({ onSubmit, isSubmitting, error }: LoginPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  return (
    <AuthShell badge="Academic System Clearance: Tier-1">
      <div className="w-full max-w-[520px] bg-surface-container-lowest border border-outline-variant rounded stamp-shadow p-8 md:p-10 relative">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center gap-2 mb-3">
            <div className="w-10 h-10 rounded bg-primary-container text-on-primary flex items-center justify-center">
              <span className="material-symbols-outlined text-2xl">history_edu</span>
            </div>
            <h1 className="font-display-lg text-headline-md md:text-[32px] text-primary tracking-tight">QuickPaperAI</h1>
          </div>
          <div className="inline-flex items-center gap-1.5 bg-surface-container-low border border-outline-variant px-2.5 py-0.5 rounded-full text-on-surface-variant mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-primary inline-block" />
            <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">
              Tuition &amp; Faculty Portal · Examiner Access
            </span>
          </div>
          <h2 className="font-headline-md text-headline-md-mobile md:text-headline-md text-on-surface mb-1">
            Sign In to Your Workspace
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Access your cloud vault, syllabus blueprints, and AI paper generator.
          </p>
        </div>

        <div className="perforated-divider mb-6" />

        <form
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(email, password);
          }}
        >
          <div className="space-y-1.5 text-left">
            <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="email">
              Institutional or Work Email
            </label>
            <div className="relative rounded">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-outline">
                <span className="material-symbols-outlined text-xl">school</span>
              </div>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="faculty@yourschool.edu"
                className="w-full pl-11 pr-4 py-2.5 bg-surface-container-lowest input-line border-b-2 text-on-surface font-label-md text-label-md transition-colors placeholder:text-outline focus:bg-surface-container-low focus:outline-none"
              />
            </div>
          </div>

          <div className="space-y-1.5 text-left">
            <div className="flex justify-between items-center">
              <label className="font-label-md text-label-md text-on-surface font-semibold" htmlFor="password">
                Password
              </label>
              <Link to="/forgot-password" className="font-label-sm text-label-sm text-secondary hover:text-primary transition-colors hover:underline">
                Forgot password?
              </Link>
            </div>
            <div className="relative rounded">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-outline">
                <span className="material-symbols-outlined text-xl">lock</span>
              </div>
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-11 pr-24 py-2.5 bg-surface-container-lowest input-line border-b-2 text-on-surface font-label-md text-label-md transition-colors placeholder:text-outline focus:bg-surface-container-low focus:outline-none tracking-wider"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center gap-1 text-on-surface-variant hover:text-primary font-label-sm text-label-sm font-medium transition-colors"
              >
                <span className="material-symbols-outlined text-lg">{showPassword ? "visibility_off" : "visibility"}</span>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {error && (
            <div className="rounded p-3 bg-error-container/60 border border-error/30 flex items-start gap-2.5 text-left" role="alert">
              <span className="material-symbols-outlined text-error shrink-0 text-xl mt-0.5">error</span>
              <div className="flex-1 text-on-error-container">
                <p className="font-label-md text-label-sm font-semibold leading-snug">Invalid credentials</p>
                <p className="font-body-md text-xs leading-normal opacity-90 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-6 bg-primary-container text-on-primary rounded font-label-md text-label-md font-bold hover:bg-primary transition-all duration-200 active:scale-[0.99] flex items-center justify-center gap-2 shadow-sm disabled:opacity-60"
            >
              <span>{isSubmitting ? "Signing in…" : "Log In"}</span>
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </button>
          </div>
        </form>

        <div className="mt-6 pt-5 border-t border-outline-variant text-center">
          <p className="font-body-md text-label-md text-on-surface-variant">
            Don't have an account?{" "}
            <Link to="/signup" className="text-primary font-semibold hover:underline font-label-md inline-flex items-center gap-0.5">
              Sign up
              <span className="material-symbols-outlined text-sm">north_east</span>
            </Link>
          </p>
        </div>

        <div className="mt-4 pt-3 flex items-center justify-center gap-1.5 text-outline text-xs">
          <span className="material-symbols-outlined text-sm material-symbols-fill">encrypted</span>
          <span className="font-label-sm text-[11px] tracking-wide text-on-surface-variant opacity-80">
            Protected by End-to-End Encryption
          </span>
        </div>
      </div>
    </AuthShell>
  );
}
