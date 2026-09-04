import { createFileRoute, Link, useNavigate, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { DeskHeader } from "@/components/desk-header";
import { Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>) => {
    return {
      redirect: (search.redirect as string) || "/",
      message: (search.message as string) || undefined,
    };
  },
  beforeLoad: ({ search }) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) {
        throw redirect({
          to: search.redirect || "/",
        });
      }
    }
  },
  head: () => ({
    meta: [
      { title: "Sign In — QuickPaperAI" },
      {
        name: "description",
        content: "Access your Examiner's Desk to draft and review practice papers.",
      },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { redirect, message } = Route.useSearch();
  const [mode, setMode] = useState<"login" | "forgot">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUnverified, setIsUnverified] = useState(false);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleVerifyUnverified() {
    if (!email) return;
    const cleanEmail = email.trim().toLowerCase();
    try {
      await api.sendOtp({ email: cleanEmail, purpose: "signup" });
    } catch {
      // Continue even if sendOtp rate limits
    }
    navigate({
      to: "/verify-otp",
      search: { email: cleanEmail, purpose: "signup" },
    });
  }

  function toggleMode(newMode: "login" | "forgot") {
    setMode(newMode);
    setError(null);
    setIsUnverified(false);
    setSuccess(false);
  }

  async function onSubmitLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsUnverified(false);
    setSuccess(false);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      return setError("Email address is required.");
    }
    if (!password) {
      return setError("Password is required.");
    }
    if (password.length < 6) {
      return setError("Password must be at least 6 characters.");
    }

    setSubmitting(true);
    try {
      const data = await api.login({ email: cleanEmail, password });
      localStorage.setItem("token", data.access_token);
      setSuccess(true);
      
      setTimeout(() => {
        navigate({ to: redirect });
      }, 500);
    } catch (err: any) {
      const msg = err.message || "";
      if (msg.toLowerCase().includes("not verified") || msg.toLowerCase().includes("verify your email")) {
        setIsUnverified(true);
        setError("Your email is not verified. Please verify your email first.");
      } else {
        setError(msg || "An unexpected error occurred during sign in.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function onSubmitForgot(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsUnverified(false);

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      return setError("Email address is required.");
    }

    setSubmitting(true);
    try {
      await api.sendOtp({ email: cleanEmail, purpose: "reset_password" });
      // Redirect to OTP verification page immediately after sending reset code
      navigate({
        to: "/verify-otp",
        search: { email: cleanEmail, purpose: "reset_password" },
      });
    } catch (err: any) {
      const msg = err.message || "";
      if (msg.toLowerCase().includes("60 seconds") || msg.includes("429")) {
        setError("Please wait 60 seconds before requesting another reset code.");
      } else {
        setError(msg || "Failed to send reset code. Please try again.");
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
                {mode === "login" ? "Logbook — Auth 01" : "Logbook — Auth 02"}
              </p>
              <h1 className="mt-3 font-serif text-4xl leading-tight">
                {mode === "login" ? (
                  <>Sign in to the <span className="italic">Desk</span>.</>
                ) : (
                  <>Reset your <span className="italic">Password</span>.</>
                )}
              </h1>
              <p className="mt-2 text-sm text-[var(--graphite)]">
                {mode === "login"
                  ? "Access your syllabus, practice papers, and draft archives."
                  : "Enter your registered email address to receive a 6-digit reset code."}
              </p>
            </div>

            {message === "signed_out" && mode === "login" && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Success:</span> signed out successfully
              </div>
            )}

            {message === "auth_required" && mode === "login" && (
              <div className="mb-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)]">
                <span className="font-bold mr-1">🔐 Required:</span> you need to log in to continue.
              </div>
            )}

            {message === "password_reset" && mode === "login" && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Success:</span> Password reset successfully! Please log in with your new password.
              </div>
            )}

            {error && (
              <div className="mb-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)] animate-shake">
                <span className="font-bold mr-1">⚠ Error:</span> {error}
                {isUnverified && (
                  <div className="mt-2 pt-2 border-t border-[var(--vermillion)]/20 flex items-center justify-between">
                    <span>Need to verify?</span>
                    <button
                      type="button"
                      onClick={handleVerifyUnverified}
                      className="font-bold underline text-[var(--vermillion)] hover:opacity-80 transition-opacity"
                    >
                      Verify Code →
                    </button>
                  </div>
                )}
              </div>
            )}

            {success && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Signed In:</span> Welcome back to the Examiner's Desk!
              </div>
            )}

            {mode === "login" ? (
              /* SIGN IN FORM */
              <form onSubmit={onSubmitLogin} className="space-y-6">
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
                  <div className="flex items-center justify-between mb-2">
                    <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)]">
                      02 · Password
                    </label>
                    <button
                      type="button"
                      onClick={() => toggleMode("forgot")}
                      className="font-mono text-[11px] uppercase tracking-[0.16em] font-semibold text-[var(--vermillion)] hover:underline-hand hover:opacity-80 transition-all flex items-center gap-1"
                    >
                      <span>Forgot password?</span>
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
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

                <div className="pt-4 flex items-center justify-between border-t border-[var(--paper-rule)]">
                  <Link
                    to="/signup"
                    className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--graphite)] hover:text-[var(--vermillion)] hover:underline-hand pb-0.5 transition-colors"
                  >
                    Create account
                  </Link>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="group inline-flex items-center gap-3 rounded-sm bg-[var(--ink)] px-6 py-3 font-mono text-xs uppercase tracking-[0.22em] text-[var(--ink-foreground)] transition hover:bg-[var(--vermillion)] disabled:opacity-50"
                  >
                    <span
                      aria-hidden
                      className="inline-block h-2 w-2 rounded-full bg-[var(--vermillion-soft)] group-hover:bg-[var(--paper)]"
                    />
                    {submitting ? "Signing in…" : "Sign In"}
                    <span aria-hidden className="opacity-60 group-hover:translate-x-1 transition">
                      →
                    </span>
                  </button>
                </div>
              </form>
            ) : (
              /* FORGOT PASSWORD FORM */
              <form onSubmit={onSubmitForgot} className="space-y-6">
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

                <div className="pt-4 flex items-center justify-between border-t border-[var(--paper-rule)]">
                  <button
                    type="button"
                    onClick={() => toggleMode("login")}
                    className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--graphite)] hover:text-[var(--vermillion)] hover:underline-hand pb-0.5 transition-colors"
                  >
                    ← Back to Sign In
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="group inline-flex items-center gap-3 rounded-sm bg-[var(--ink)] px-6 py-3 font-mono text-xs uppercase tracking-[0.22em] text-[var(--ink-foreground)] transition hover:bg-[var(--vermillion)] disabled:opacity-50"
                  >
                    <span
                      aria-hidden
                      className="inline-block h-2 w-2 rounded-full bg-[var(--vermillion-soft)] group-hover:bg-[var(--paper)]"
                    />
                    {submitting ? "Sending…" : "Send Reset Code"}
                    <span aria-hidden className="opacity-60 group-hover:translate-x-1 transition">
                      →
                    </span>
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
