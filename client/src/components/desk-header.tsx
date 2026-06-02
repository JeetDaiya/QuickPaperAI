import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

interface DeskHeaderProps {
  variant?: "paper" | "ink";
  threadId?: string;
  step?: 1 | 2 | 3 | 4;
  hideNav?: boolean;
}

const STEPS = [
  { n: 1, label: "Request" },
  { n: 2, label: "Generate" },
  { n: 3, label: "Review" },
  { n: 4, label: "Export" },
] as const;

export function DeskHeader({ variant = "paper", step, hideNav = false }: DeskHeaderProps) {
  const onInk = variant === "ink";
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setIsLoggedIn(!!localStorage.getItem("token"));
    }
  }, []);

  const handleSignOut = () => {
    localStorage.removeItem("token");
    setIsLoggedIn(false);
    navigate({ to: "/login" });
  };

  return (
    <header
      className={`border-b ${onInk ? "border-[var(--ink-rule)]" : "border-[var(--paper-rule)]"}`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link
          to="/"
          className="flex items-baseline gap-2 font-serif text-2xl leading-none"
        >
          <span
            aria-hidden
            className="inline-block h-3 w-3 rounded-full"
            style={{ background: "var(--vermillion)" }}
          />
          <span>QuickPaper</span>
          <span className="font-mono text-xs uppercase tracking-[0.2em] opacity-60">
            ai
          </span>
        </Link>

        {step ? (
          <ol className="hidden items-center gap-3 font-mono text-[11px] uppercase tracking-[0.18em] md:flex">
            {STEPS.map((s, i) => {
              const state =
                s.n < step ? "done" : s.n === step ? "active" : "pending";
              return (
                <li key={s.n} className="flex items-center gap-3">
                  <span
                    className={
                      state === "active"
                        ? "underline-hand pb-1"
                        : state === "done"
                          ? "opacity-60"
                          : "opacity-30"
                    }
                  >
                    <span className="mr-1">{String(s.n).padStart(2, "0")}</span>
                    {s.label}
                  </span>
                  {i < STEPS.length - 1 ? (
                    <span aria-hidden className="opacity-30">
                      —
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ol>
        ) : !hideNav ? (
          <nav className="flex items-center gap-6 font-mono text-xs uppercase tracking-[0.2em] opacity-70">
            <Link to="/new" className="hover:underline-hand pb-1">
              New paper
            </Link>
            {isLoggedIn && (
              <button
                onClick={handleSignOut}
                className="hover:underline-hand pb-1 text-[var(--vermillion)] cursor-pointer bg-transparent border-none p-0 outline-none"
              >
                Sign out
              </button>
            )}
          </nav>
        ) : null}
      </div>
    </header>
  );
}
