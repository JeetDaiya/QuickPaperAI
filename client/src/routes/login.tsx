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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!email.trim()) {
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
      const data = await api.login({ email, password });
      localStorage.setItem("token", data.access_token);
      setSuccess(true);
      
      // Delay navigation slightly so they see the success state
      setTimeout(() => {
        navigate({ to: redirect });
      }, 500);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during sign in.");
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
                Logbook — Auth 01
              </p>
              <h1 className="mt-3 font-serif text-4xl leading-tight">
                Sign in to the <span className="italic">Desk</span>.
              </h1>
              <p className="mt-2 text-sm text-[var(--graphite)]">
                Access your syllabus, practice papers, and draft archives.
              </p>
            </div>

            {message === "signed_out" && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Success:</span> signed out successfully
              </div>
            )}

            {message === "auth_required" && (
              <div className="mb-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)]">
                <span className="font-bold mr-1">🔐 Required:</span> you need to log in to continue.
              </div>
            )}

            {error && (
              <div className="mb-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)] animate-shake">
                <span className="font-bold mr-1">⚠ Error:</span> {error}
              </div>
            )}

            {success && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Signed In:</span> Welcome back to the Examiner's Desk!
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
                  02 · Password
                </label>
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
          </div>
        </div>
      </main>
    </div>
  );
}
