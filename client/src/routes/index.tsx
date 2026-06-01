import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DeskHeader } from "@/components/desk-header";
import { loadDrafts, type DraftRecord, getActiveThread } from "@/lib/drafts";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "QuickPaperAI — Your Examiner's Desk" },
      {
        name: "description",
        content:
          "A teacher's drafting table for AI-generated question papers. Recent drafts, syllabus presets, and a review-then-publish workflow.",
      },
    ],
  }),
  component: Home,
});

function Home() {
  const [drafts, setDrafts] = useState<DraftRecord[]>([]);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    setDrafts(loadDrafts());
    setActive(getActiveThread());
  }, []);

  return (
    <div className="min-h-screen surface-paper">
      <DeskHeader />

      <main className="mx-auto max-w-6xl px-6 pt-20 pb-24 md:pl-28">
        <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--graphite)]">
          01 — Examiner's Desk
        </p>
        <h1 className="mt-6 font-serif text-[clamp(2.6rem,6vw,4.5rem)] leading-[1.12] tracking-tight">
          Set a paper the way <span className="italic">you</span> would,
          <br />
          <span className="underline-hand pb-2">just faster.</span>
        </h1>
        <p className="mt-8 max-w-xl text-lg leading-relaxed text-[var(--graphite)]">
          QuickPaper drafts question candidates from your syllabus, lays them
          out by chapter and type, and waits for you to tick the ones you
          want. No black box, no surprises in the printout.
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-4">
          <Link
            to="/new"
            className="group inline-flex items-center gap-3 rounded-sm bg-[var(--ink)] px-6 py-3 font-mono text-xs uppercase tracking-[0.22em] text-[var(--ink-foreground)] transition hover:bg-[var(--vermillion)]"
          >
            <span
              aria-hidden
              className="inline-block h-2 w-2 rounded-full bg-[var(--vermillion-soft)] group-hover:bg-[var(--paper)]"
            />
            Begin a new paper
            <span aria-hidden className="opacity-60 group-hover:translate-x-1 transition">
              →
            </span>
          </Link>
          {active ? (
            <Link
              to="/papers/$threadId/progress"
              params={{ threadId: active }}
              className="font-mono text-xs uppercase tracking-[0.2em] underline-hand pb-1"
            >
              Resume last session
            </Link>
          ) : null}
        </div>

        <section className="mt-20 grid gap-10 md:grid-cols-[2fr_3fr]">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--graphite)]">
              Recent drafts
            </p>
            <h2 className="mt-2 font-serif text-3xl">From the pile</h2>
            <p className="mt-3 text-sm text-[var(--graphite)]">
              Pick up any draft you started. Sessions persist locally — no
              account needed.
            </p>
          </div>

          <ul className="space-y-3">
            {drafts.length === 0 ? (
              <li className="rounded-sm border border-dashed border-[var(--paper-rule)] bg-[var(--card)] px-5 py-6 text-sm text-[var(--graphite)]">
                <span className="font-mono uppercase tracking-[0.18em] text-[10px] opacity-70">
                  — empty desk —
                </span>
                <p className="mt-2">
                  Your first generated paper will land here. Try starting one.
                </p>
              </li>
            ) : (
              drafts.map((d) => (
                <li key={d.threadId}>
                  <Link
                    to="/papers/$threadId/progress"
                    params={{ threadId: d.threadId }}
                    className="group flex items-baseline justify-between gap-4 border-b border-[var(--paper-rule)] py-4 transition hover:bg-[var(--card)]"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-serif text-xl">
                        {d.institution || "Untitled institution"}
                      </div>
                      <div className="mt-1 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--graphite)]">
                        {d.subject} · {d.standard}
                        {d.status ? (
                          <span className="ml-2 text-[var(--vermillion)]">
                            {d.status}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <div className="shrink-0 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--graphite)] opacity-70 group-hover:opacity-100">
                      {new Date(d.createdAt).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                      })}
                      <span className="ml-2 opacity-60 group-hover:translate-x-0.5 inline-block transition">
                        →
                      </span>
                    </div>
                  </Link>
                </li>
              ))
            )}
          </ul>
        </section>
      </main>
    </div>
  );
}
