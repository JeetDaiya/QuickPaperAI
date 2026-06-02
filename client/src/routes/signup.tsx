import { createFileRoute, Link, useNavigate, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { DeskHeader } from "@/components/desk-header";
import { Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";

export const Route = createFileRoute("/signup")({
  beforeLoad: () => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) {
        throw redirect({
          to: "/",
        });
      }
    }
  },
  head: () => ({
    meta: [
      { title: "Sign Up — QuickPaperAI" },
      {
        name: "description",
        content: "Register a new account to manage and generate exam practice papers.",
      },
    ],
  }),
  component: SignupPage,
});

function SignupPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!name.trim()) {
      return setError("Name is required.");
    }
    if (!email.trim()) {
      return setError("Email address is required.");
    }
    if (!password) {
      return setError("Password is required.");
    }
    if (password.length < 6) {
      return setError("Password must be at least 6 characters.");
    }
    if (password !== confirmPassword) {
      return setError("Passwords do not match.");
    }

    setSubmitting(true);
    try {
      await api.register({ email, password, name });
      setSuccess(true);
      
      // Delay navigation to let the user see the success feedback
      setTimeout(() => {
        navigate({ to: "/login" });
      }, 1500);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during registration.");
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
                Logbook — Auth 02
              </p>
              <h1 className="mt-3 font-serif text-4xl leading-tight">
                Create your <span className="italic">Ledger</span>.
              </h1>
              <p className="mt-2 text-sm text-[var(--graphite)]">
                Sign up as an examiner to generate and publish practice papers.
              </p>
            </div>

            {error && (
              <div className="mb-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)] animate-shake">
                <span className="font-bold mr-1">⚠ Error:</span> {error}
              </div>
            )}

            {success && (
              <div className="mb-6 border border-emerald-600 bg-emerald-50 px-4 py-3 font-mono text-xs text-emerald-800">
                <span className="font-bold mr-1">✓ Registered:</span> Account created successfully! Redirecting to login...
              </div>
            )}

            <form onSubmit={onSubmit} className="space-y-6">
              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] mb-2">
                  01 · Full Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Alex Mercer"
                  className="w-full border-b border-[var(--paper-rule)] bg-transparent pb-2 font-serif text-xl outline-none focus:border-[var(--vermillion)] transition-colors"
                />
              </div>

              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] mb-2">
                  02 · Email Address
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
                  03 · Password
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

              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] mb-2">
                  04 · Confirm Password
                </label>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full border-b border-[var(--paper-rule)] bg-transparent pb-2 font-mono text-lg outline-none focus:border-[var(--vermillion)] transition-colors"
                />
              </div>

              <div className="pt-4 flex items-center justify-between border-t border-[var(--paper-rule)]">
                <Link
                  to="/login"
                  className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--graphite)] hover:text-[var(--vermillion)] hover:underline-hand pb-0.5 transition-colors"
                >
                  Already registered?
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
                  {submitting ? "Registering…" : "Register"}
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
