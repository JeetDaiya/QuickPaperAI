import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { DeskHeader } from "@/components/desk-header";
import { api } from "@/lib/api";
import {
  isObjective,
  SECTION_ORDER,
  TYPE_LABEL,
} from "@/lib/paper-config";
import type { QuestionCandidate } from "@/lib/types";

export const Route = createFileRoute("/papers/$threadId/review")({
  head: () => ({
    meta: [
      { title: "Review — QuickPaperAI" },
      {
        name: "description",
        content: "Pick the question candidates you want on the final paper.",
      },
    ],
  }),
  component: ReviewPage,
});

// Safe dynamic KaTeX loaded check
function getKatex(): any {
  if (typeof window !== "undefined") {
    return (window as any).katex;
  }
  return null;
}

// Auto-wrap precise chemical formulas like H_2SO_4 or H^+ that aren't delimited with $
function autoWrapMath(text: string): string {
  if (!text) return text;
  if (text.includes("$")) return text;
  
  // Match precise, space-free chemical formulas and simple sub/superscript tokens
  // 1. Matches words with subscripts like H_2SO_4, Mg(OH)_2, CO_3, etc.
  // 2. Matches words with superscripts like H^+, OH^-, Al^{3+}, etc.
  // 3. Matches LaTeX backslash macros like \theta, \times, \Delta, \mu
  return text.replace(
    /(\b[A-Z][a-z]?[\(\)\w]*[\_\^][\w\+\-\{\}\(\)]+\b|\b[a-zA-Z0-9\(\)]+[\_\^][\+\-]\b|\\[a-zA-Z]+(?:\{[^\}]*\})*)/g,
    (match) => `$${match}$`
  );
}

export function Latex({ text }: { text: string }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (getKatex()) {
      setLoaded(true);
      return;
    }
    const interval = setInterval(() => {
      if (getKatex()) {
        setLoaded(true);
        clearInterval(interval);
      }
    }, 100);
    return () => clearInterval(interval);
  }, []);

  if (!text) return null;

  const processedText = autoWrapMath(text);
  const katex = getKatex();
  if (!loaded || !katex) {
    return <span>{processedText}</span>;
  }

  try {
    const parts: { type: "text" | "inline" | "block"; content: string }[] = [];
    
    // Split by block math $$
    const blockParts = processedText.split(/\$\$(.*?)\$\$/gs);
    for (let i = 0; i < blockParts.length; i++) {
      if (i % 2 === 1) {
        parts.push({ type: "block", content: blockParts[i] });
      } else {
        // Split by inline math $
        const inlineParts = blockParts[i].split(/\$(.*?)\$/g);
        for (let j = 0; j < inlineParts.length; j++) {
          if (j % 2 === 1) {
            parts.push({ type: "inline", content: inlineParts[j] });
          } else {
            if (inlineParts[j]) {
              parts.push({ type: "text", content: inlineParts[j] });
            }
          }
        }
      }
    }

    return (
      <span>
        {parts.map((part, index) => {
          if (part.type === "block") {
            const html = katex.renderToString(part.content, {
              displayMode: true,
              throwOnError: false,
            });
            return (
              <span
                key={index}
                className="block my-2 overflow-x-auto"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            );
          } else if (part.type === "inline") {
            const html = katex.renderToString(part.content, {
              displayMode: false,
              throwOnError: false,
            });
            return (
              <span
                key={index}
                className="inline-block"
                dangerouslySetInnerHTML={{ __html: html }}
              />
            );
          } else {
            return <span key={index}>{part.content}</span>;
          }
        })}
      </span>
    );
  } catch (err) {
    console.error("Error parsing LaTeX:", err);
    return <span>{text}</span>;
  }
}

// Indexed candidate — preserves the original position in `questions[]`,
// which is what /api/resume expects in `selected_indices`.
interface IndexedCandidate {
  index: number;
  q: QuestionCandidate;
}

function ReviewPage() {
  const { threadId } = Route.useParams();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["status", threadId],
    queryFn: () => api.status(threadId),
    refetchInterval: (q) =>
      q.state.data?.status === "awaiting_review" ? false : 1500,
  });

  const reviewData = data?.status === "awaiting_review" ? data : null;
  const indexed: IndexedCandidate[] = useMemo(
    () =>
      (reviewData?.questions ?? []).map((q, index) => ({ index, q })),
    [reviewData],
  );

  const byChapter = useMemo(() => {
    const out: Record<string, IndexedCandidate[]> = {};
    for (const c of indexed) (out[c.q.chapter] ??= []).push(c);
    return out;
  }, [indexed]);

  const chapters = useMemo(() => {
    return Object.keys(byChapter).sort();
  }, [byChapter]);

  const targets = reviewData?.targets ?? { objective: 0, subjective: 0 };
  const tally = useMemo(
    () => computeTally(indexed, selected),
    [indexed, selected],
  );

  function toggle(i: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  function handleSelectAll() {
    const allSelected = selected.size === indexed.length;
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(indexed.map((x) => x.index)));
    }
  }

  async function onSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.resume(threadId, {
        selected_indices: Array.from(selected).sort((a, b) => a - b),
      });
      navigate({
        to: "/papers/$threadId/done",
        params: { threadId },
        replace: true,
      });
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "Submission failed.");
      setSubmitting(false);
    }
  }

  return (
    <div
      className="min-h-screen surface-paper"
      style={{ ["--margin-x" as string]: "0px" }}
    >
      <DeskHeader step={3} />

      <TallyBar
        tally={tally}
        targets={targets}
        onSubmit={onSubmit}
        submitting={submitting}
        canSubmit={selected.size > 0}
        totalCount={indexed.length}
        selectedCount={selected.size}
        onSelectAll={handleSelectAll}
      />

      <main className="mx-auto max-w-6xl px-6 pt-16 pb-24">
        <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--graphite)]">
          Sheet 03 — Review candidates
        </p>
        <h1 className="mt-6 font-serif text-5xl">Tick what stays.</h1>
        <p className="mt-6 max-w-xl text-[var(--graphite)]">
          Candidates are stacked by chapter, sorted by section. The tally
          above is advisory — submit whenever you're ready, even if counts
          don't match exactly.
        </p>

        {isLoading ? (
          <p className="mt-12 font-mono text-xs uppercase tracking-[0.2em] opacity-60">
            Loading candidate stack…
          </p>
        ) : error ? (
          <p className="mt-12 font-mono text-xs uppercase tracking-[0.2em] text-[var(--vermillion)]">
            {(error as Error).message}
          </p>
        ) : !reviewData ? (
          <p className="mt-12 font-mono text-xs uppercase tracking-[0.2em] opacity-60">
            Backend is not in awaiting_review state yet.
          </p>
        ) : chapters.length === 0 ? (
          <p className="mt-12 font-mono text-xs uppercase tracking-[0.2em] opacity-60">
            No candidates were generated.
          </p>
        ) : (
          <div className="mt-10 space-y-16">
            {chapters.map((chapterName) => {
              const chapterQuestions = byChapter[chapterName];
              const sortedQuestions = sortBySection(chapterQuestions);
              const sel = chapterQuestions.filter((s) => selected.has(s.index)).length;
              return (
                <section key={chapterName} className="border-t border-[var(--paper-rule)] pt-10 first:border-none first:pt-0">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="font-serif text-3xl text-[var(--paper-foreground)]">
                      {chapterName}
                    </h2>
                    <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--graphite)]">
                      {sel}/{chapterQuestions.length} picked
                    </span>
                  </div>
                  <ChapterStack
                    items={sortedQuestions}
                    selected={selected}
                    onToggle={toggle}
                  />
                </section>
              );
            })}
          </div>
        )}

        {submitError ? (
          <div className="mt-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)]">
            {submitError}
          </div>
        ) : null}
      </main>
    </div>
  );
}

function sortBySection(list: IndexedCandidate[]) {
  return [...list].sort(
    (a, b) =>
      SECTION_ORDER.indexOf(a.q.question_type) -
      SECTION_ORDER.indexOf(b.q.question_type),
  );
}

interface Tally {
  objective: number;
  subjective: number;
  marks: number;
}
function computeTally(items: IndexedCandidate[], selected: Set<number>): Tally {
  const t: Tally = { objective: 0, subjective: 0, marks: 0 };
  for (const { index, q } of items) {
    if (!selected.has(index)) continue;
    if (isObjective(q.question_type)) t.objective++;
    else t.subjective++;
    t.marks += q.marks ?? 0;
  }
  return t;
}

function TallyBar({
  tally,
  targets,
  onSubmit,
  submitting,
  canSubmit,
  totalCount,
  selectedCount,
  onSelectAll,
}: {
  tally: Tally;
  targets: { objective: number; subjective: number };
  onSubmit: () => void;
  submitting: boolean;
  canSubmit: boolean;
  totalCount: number;
  selectedCount: number;
  onSelectAll: () => void;
}) {
  const mismatch =
    tally.objective !== targets.objective ||
    tally.subjective !== targets.subjective;
  const allSelected = selectedCount === totalCount;
  return (
    <div className="sticky top-0 z-20 border-b border-[var(--paper-rule)] bg-[var(--card)]/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 font-mono text-[11px] uppercase tracking-[0.18em]">
        <div className="flex flex-wrap items-center gap-5 justify-between sm:justify-start">
          {targets.objective > 0 && (
            <TallyChip
              label="Objective"
              value={tally.objective}
              target={targets.objective}
            />
          )}
          {targets.subjective > 0 && (
            <TallyChip
              label="Subjective"
              value={tally.subjective}
              target={targets.subjective}
            />
          )}
          <div>
            Σ <span className="text-[var(--vermillion)]">{tally.marks}</span>{" "}
            marks
          </div>
        </div>
        <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              type="button"
              onClick={onSelectAll}
              className="group inline-flex items-center justify-center gap-1.5 border border-[var(--paper-rule)] bg-[var(--card)] px-4 py-2.5 text-[var(--paper-foreground)] hover:border-[var(--vermillion)] hover:stamp-shadow transition flex-1 sm:flex-none text-center"
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  allSelected ? "bg-[var(--vermillion)]" : "bg-[var(--graphite)]/30"
                }`}
              />
              {allSelected ? "Deselect" : "Select all"}
            </button>

            <button
              onClick={onSubmit}
              disabled={!canSubmit || submitting}
              className="group inline-flex items-center justify-center gap-2 bg-[var(--ink)] px-5 py-2.5 text-[var(--ink-foreground)] disabled:opacity-40 hover:bg-[var(--vermillion)] transition flex-1 sm:flex-none text-center"
            >
              <span
                aria-hidden
                className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--vermillion-soft)] group-hover:bg-[var(--paper)]"
              />
              {submitting ? "Submitting…" : "Submit"}
              <span aria-hidden>→</span>
            </button>
          </div>

          {mismatch ? (
            <span className="inline-flex items-center justify-center gap-2 rounded-full bg-[var(--vermillion)]/10 px-3.5 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--vermillion)] border border-[var(--vermillion)]/20 animate-pulse w-full sm:w-auto text-center">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--vermillion)]" />
              ⚠ mismatch — submit anyway
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function TallyChip({
  label,
  value,
  target,
}: {
  label: string;
  value: number;
  target: number;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="opacity-60">{label}:</span>
      <span>
        <span className="text-[var(--vermillion)] font-bold">{value}</span>
        <span className="opacity-50">/{target}</span>
      </span>
    </div>
  );
}

function ChapterStack({
  items,
  selected,
  onToggle,
}: {
  items: IndexedCandidate[];
  selected: Set<number>;
  onToggle: (i: number) => void;
}) {
  let lastSection = "";
  return (
    <div className="mt-8 space-y-6">
      {items.map(({ index, q }) => {
        const sectionLabel = TYPE_LABEL[q.question_type] ?? q.question_type;
        const showHeader = q.question_type !== lastSection;
        lastSection = q.question_type;
        return (
          <div key={index}>
            {showHeader ? (
              <h3 className="mb-3 font-mono text-[11px] uppercase tracking-[0.22em] text-[var(--graphite)]">
                — {sectionLabel} —
              </h3>
            ) : null}
            <IndexCard
              candidate={q}
              selected={selected.has(index)}
              onToggle={() => onToggle(index)}
            />
          </div>
        );
      })}
    </div>
  );
}

function IndexCard({
  candidate,
  selected,
  onToggle,
}: {
  candidate: QuestionCandidate;
  selected: boolean;
  onToggle: () => void;
}) {
  const [open, setOpen] = useState(false);
  const hasOptions = candidate.options && candidate.options.length > 0;
  const hasEvalScheme =
    candidate.evaluation_scheme && candidate.evaluation_scheme.length > 0;
  const isMatchTheColumn = candidate.question_type === "MATCH_THE_COLUMN";
  const hasPipe = candidate.options && candidate.options.some((opt) => opt.includes("|"));

  return (
    <article
      className={`relative grid grid-cols-[3rem_1fr] gap-0 border bg-[var(--card)] transition ${
        selected
          ? "border-[var(--vermillion)] stamp-shadow"
          : "border-[var(--paper-rule)] hover:border-[var(--graphite)]"
      }`}
    >
      <button
        onClick={onToggle}
        aria-pressed={selected}
        className={`relative flex flex-col items-center justify-start gap-2 border-r border-[var(--paper-rule)] py-5 perforated-left ${
          selected ? "bg-[var(--vermillion)]/8" : ""
        }`}
      >
        <span
          aria-hidden
          className={`inline-flex h-6 w-6 items-center justify-center border ${
            selected
              ? "border-[var(--vermillion)] bg-[var(--vermillion)] text-[var(--paper)]"
              : "border-[var(--graphite)] text-transparent"
          }`}
        >
          ✓
        </span>
        <span className="rotate-180 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] [writing-mode:vertical-rl]">
          {candidate.marks ?? 1} mk
        </span>
      </button>

      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <p className="font-serif text-xl leading-snug">
            <Latex text={candidate.question_text} />
          </p>
          {candidate.diagram_prompt ? (
            <span
              title={candidate.diagram_prompt}
              className="shrink-0 border border-[var(--graphite)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--graphite)]"
            >
              📷 diagram
            </span>
          ) : null}
        </div>

        {hasOptions ? (
          isMatchTheColumn && hasPipe ? (
            <div className="mt-4 overflow-x-auto border border-[var(--paper-rule)] bg-[var(--paper)]/40 p-1">
              <table className="w-full text-left border-collapse font-mono text-[10px] uppercase tracking-wider">
                <thead>
                  <tr className="border-b border-[var(--paper-rule)] bg-[var(--graphite)]/5 text-[var(--graphite)] font-bold">
                    <th className="px-4 py-2 border-r border-[var(--paper-rule)] w-1/2">Column A</th>
                    <th className="px-4 py-2 w-1/2">Column B</th>
                  </tr>
                </thead>
                <tbody className="font-serif text-sm normal-case tracking-normal text-[var(--paper-foreground)]/85">
                  {candidate.options.map((opt, i) => {
                    const parts = opt.split("|");
                    const colA = parts[0]?.trim() ?? "";
                    const colB = parts[1]?.trim() ?? "";
                    return (
                      <tr key={i} className="border-b border-[var(--paper-rule)] last:border-none hover:bg-[var(--vermillion)]/[0.02]">
                        <td className="px-4 py-2 border-r border-[var(--paper-rule)]">
                          <Latex text={colA} />
                        </td>
                        <td className="px-4 py-2">
                          <Latex text={colB} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <ol className="mt-3 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {candidate.options.map((opt, i) => {
                const letter = String.fromCharCode(65 + i);
                const isCorrect = candidate.correct_answer === letter;
                return (
                  <li
                    key={i}
                    className="flex gap-2 text-sm text-[var(--paper-foreground)]/85"
                  >
                    <span
                      className={`font-mono ${
                        isCorrect
                          ? "text-[var(--vermillion)]"
                          : "text-[var(--graphite)]"
                      }`}
                    >
                      ({letter})
                    </span>
                    <span className={isCorrect ? "underline-hand pb-0.5" : ""}>
                      <Latex text={opt} />
                    </span>
                  </li>
                );
              })}
            </ol>
          )
        ) : null}

        <div className="mt-4">
          <button
            onClick={() => setOpen((v) => !v)}
            className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)] hover:text-[var(--vermillion)]"
          >
            {open ? "▾" : "▸"} answer key
            {hasEvalScheme
              ? ` · ${candidate.evaluation_scheme.length}-point scheme`
              : ""}
          </button>
          {open ? (
            <div className="mt-2 border-l-2 border-[var(--vermillion)] bg-[var(--accent)]/40 p-3">
              <p className="font-serif text-sm italic">
                <Latex text={candidate.answer} />
              </p>
              {hasEvalScheme ? (
                <ul className="mt-3 space-y-1">
                  {candidate.evaluation_scheme.map((p, i) => (
                    <li
                      key={i}
                      className="flex items-baseline gap-2 font-mono text-[11px]"
                    >
                      <span className="text-[var(--vermillion)]">
                        +{p.allocated_marks}
                      </span>
                      <span className="text-[var(--paper-foreground)]/80">
                        <Latex text={p.point_text} />
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}
