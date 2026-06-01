import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { DeskHeader } from "@/components/desk-header";
import { api } from "@/lib/api";
import { updateDraftStatus } from "@/lib/drafts";
import type { ChapterProgress } from "@/lib/types";

export const Route = createFileRoute("/papers/$threadId/progress")({
  head: () => ({
    meta: [
      { title: "Generating — QuickPaperAI" },
      {
        name: "description",
        content: "Live progress of chapter-by-chapter question generation.",
      },
    ],
  }),
  component: ProgressPage,
});

function ProgressPage() {
  const { threadId } = Route.useParams();
  const navigate = useNavigate();

  const { data, error, isLoading } = useQuery({
    queryKey: ["status", threadId],
    queryFn: () => api.status(threadId),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" || s === "awaiting_review"
        ? false
        : 1500;
    },
  });

  useEffect(() => {
    if (!data) return;
    updateDraftStatus(threadId, labelFor(data.status));
    if (data.status === "awaiting_review") {
      navigate({
        to: "/papers/$threadId/review",
        params: { threadId },
        replace: true,
      });
    } else if (data.status === "completed") {
      navigate({
        to: "/papers/$threadId/done",
        params: { threadId },
        replace: true,
      });
    }
  }, [data, navigate, threadId]);

  const chapters: ChapterProgress[] =
    data?.status === "generating" || data?.status === "failed"
      ? Object.values(data.progress ?? {})
      : [];

  const failedChapters = chapters.filter((c) => c.status === "failed");

  return (
    <div className="min-h-screen surface-ink">
      <DeskHeader variant="ink" step={2} />

      <main className="mx-auto max-w-6xl px-6 pt-12 pb-24">
        <div className="flex items-baseline justify-between gap-6">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--vermillion-soft)]">
              Sheet 02 — Live ledger
            </p>
            <h1 className="mt-3 font-serif text-5xl">
              The pipeline is running<span className="cursor-blink" />
            </h1>
            <p className="mt-3 max-w-xl text-sm text-[var(--ink-foreground)]/70">
              Each chapter runs{" "}
              <span className="font-mono">retrieve → distil → compile</span>{" "}
              concurrently. You'll be pulled into the review desk the moment
              candidates are ready.
            </p>
          </div>
          <div className="hidden text-right font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--ink-foreground)]/40 md:block">
            thread
            <div className="mt-1 break-all text-[var(--ink-foreground)]/70">
              {threadId.slice(0, 18)}…
            </div>
          </div>
        </div>

        {isLoading ? (
          <p className="mt-12 font-mono text-xs uppercase tracking-[0.2em] opacity-60">
            Connecting to /api/status…
          </p>
        ) : error ? (
          <ErrorBlock
            title="Couldn't reach the generator."
            message={(error as Error).message}
          />
        ) : data?.status === "uninitialized" ? (
          <div className="mt-12">
            <p className="font-mono text-xs uppercase tracking-[0.2em] opacity-60">
              Initializing thread — opening the ledger…
            </p>
            <div className="mt-6 h-px w-48 bg-[var(--ink-rule)] overflow-hidden">
              <div
                className="h-full w-1/3 animate-ledger"
                style={{ background: "var(--vermillion)" }}
              />
            </div>
          </div>
        ) : data?.status === "failed" ? (
          <>
            <ErrorBlock
              title="The pipeline halted."
              message={
                data.error ??
                (failedChapters.length > 0
                  ? `${failedChapters.length} chapter(s) failed during generation.`
                  : "Generation failed before any candidates were produced.")
              }
            />
            {chapters.length > 0 && (
              <div className="mt-10">
                <StitchedLedger chapters={chapters} />
              </div>
            )}
          </>
        ) : (
          <div className="mt-12">
            <StitchedLedger chapters={chapters} />
          </div>
        )}

        <div className="mt-16">
          <Link
            to="/"
            className="font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--ink-foreground)]/60 hover:text-[var(--vermillion-soft)]"
          >
            ← back to desk
          </Link>
        </div>
      </main>
    </div>
  );
}

function labelFor(s: string) {
  if (s === "generating") return "Generating";
  if (s === "awaiting_review") return "Awaiting review";
  if (s === "completed") return "Ready";
  if (s === "failed") return "Failed";
  return s;
}

function StitchedLedger({ chapters }: { chapters: ChapterProgress[] }) {
  if (chapters.length === 0) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.2em] opacity-60">
        Waiting for chapter fan-out…
      </p>
    );
  }
  return (
    <ol className="space-y-5">
      {chapters.map((ch, i) => {
        const pct =
          ch.status === "completed"
            ? 1
            : ch.status === "processing"
              ? 0.55
              : ch.status === "failed"
                ? 0.3
                : 0.08;
        const isDone = ch.status === "completed";
        const isFailed = ch.status === "failed";
        return (
          <li key={ch.chapter} className="grid grid-cols-[2.5rem_1fr] gap-4">
            <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--ink-foreground)]/40 pt-1">
              {String(i + 1).padStart(2, "0")}
            </div>
            <div>
              <div className="flex items-baseline justify-between gap-4">
                <h3 className="font-serif text-2xl leading-tight">
                  {ch.chapter}
                </h3>
                <div className="font-mono text-[11px] uppercase tracking-[0.18em]">
                  <span className="text-[var(--vermillion-soft)]">
                    {ch.generated_count}
                  </span>
                  <span className="opacity-50"> · candidates</span>
                </div>
              </div>
              <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--ink-foreground)]/40">
                {isDone
                  ? "✓ complete"
                  : isFailed
                    ? "✗ failed"
                    : ch.status === "processing"
                      ? "● processing"
                      : "○ pending"}
              </div>
              <div className="mt-3 relative h-px bg-[var(--ink-rule)]">
                <div
                  className="absolute inset-y-0 left-0 h-[2px] -top-px animate-ledger"
                  style={{
                    width: `${pct * 100}%`,
                    background: isFailed
                      ? "var(--vermillion)"
                      : isDone
                        ? "var(--vermillion-soft)"
                        : "linear-gradient(90deg, var(--vermillion) 0%, transparent 100%)",
                  }}
                />
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function ErrorBlock({ title, message }: { title?: string; message: string }) {
  return (
    <div className="mt-12 border border-[var(--vermillion)] bg-[var(--vermillion)]/10 p-6">
      <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--vermillion-soft)]">
        Pipeline error
      </p>
      <p className="mt-2 font-serif text-2xl">
        {title ?? "Couldn't reach the generator."}
      </p>
      <p className="mt-2 font-mono text-xs text-[var(--ink-foreground)]/70">
        {message}
      </p>
      <p className="mt-4 text-sm text-[var(--ink-foreground)]/60">
        Confirm the FastAPI server is running on{" "}
        <span className="font-mono">localhost:8000</span> and CORS allows this
        origin.
      </p>
    </div>
  );
}
