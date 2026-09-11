import { useMemo, useState } from "react";
import { Latex } from "@/components/Latex";
import type { Question } from "@/lib/api/types";

const DIFFICULTY_STYLE: Record<string, string> = {
  Easy: "bg-tertiary-container text-on-tertiary-container",
  Medium: "bg-surface-variant text-on-surface-variant",
  Hard: "bg-error-container text-on-error-container",
};

export interface ReviewPageProps {
  questions: Question[];
  targets: { objective: number; subjective: number };
  onFinalize: (selectedIndices: number[]) => void;
  isSubmitting: boolean;
  error?: string;
}

const TYPE_LABEL: Record<string, string> = {
  MCQ: "MCQ",
  FILL_IN_THE_BLANK: "Fill in the Blank",
  MATCH_THE_COLUMN: "Match the Column",
  TRUE_FALSE: "True / False",
  ONE_WORD_ANS: "One Word",
  "2_MARKS": "2 Marks",
  "3_MARKS": "3 Marks",
  "4_MARKS": "4 Marks",
};

export function ReviewPage({ questions, targets, onFinalize, isSubmitting, error }: ReviewPageProps) {
  const chapters = useMemo(() => [...new Set(questions.map((q) => q.chapter))], [questions]);
  const [activeChapter, setActiveChapter] = useState(chapters[0] ?? "");
  const [selected, setSelected] = useState<Set<number>>(new Set(questions.map((_, i) => i)));

  function toggle(index: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  const totalMarks = questions.reduce((sum, q, i) => (selected.has(i) ? sum + q.marks : sum), 0);
  const targetTotal = targets.objective + targets.subjective;

  return (
    <div className="text-on-surface font-body-md min-h-screen flex flex-col">
      <div className="bg-surface border-b border-outline-variant px-margin-mobile md:px-margin-desktop pt-8 pb-4">
        <div className="max-w-container-max mx-auto">
          <span className="font-label-sm text-secondary uppercase tracking-widest mb-1 block">Human-in-the-Loop Review</span>
          <h2 className="font-display-lg text-headline-md md:text-display-lg text-on-surface">Question Selection</h2>
          <p className="font-body-md text-on-surface-variant mt-2 max-w-2xl">
            Review the AI-generated questions and select the ones to include in the final paper.
          </p>

          <div className="flex gap-2 overflow-x-auto mt-6">
            {chapters.map((ch) => (
              <button
                key={ch}
                onClick={() => setActiveChapter(ch)}
                className={`px-6 py-2 border border-b-0 rounded-t-lg font-label-md whitespace-nowrap ${
                  ch === activeChapter ? "bg-surface-container-lowest text-on-surface border-outline-variant shadow-sm relative z-10" : "bg-surface-container text-on-surface-variant border-outline-variant hover:bg-surface-container-high"
                }`}
              >
                {ch} ({questions.filter((q) => q.chapter === ch).length})
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-grow bg-surface-container-lowest p-margin-mobile md:p-margin-desktop">
        <div className="max-w-container-max mx-auto flex flex-col lg:flex-row gap-gutter">
          <div className="flex-grow flex flex-col gap-6 lg:w-2/3 pb-24">
            {questions.map((q, i) => {
              if (q.chapter !== activeChapter) return null;
              const isSelected = selected.has(i);
              return (
                <div
                  key={i}
                  className={`bg-surface border rounded-r-lg p-6 transition-all relative ${
                    isSelected ? "border-l-4 border-l-primary border-y-outline-variant border-r-outline-variant stamp-shadow" : "border-outline-variant"
                  }`}
                >
                  <div className="flex justify-between items-start mb-4 gap-4">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="bg-primary-container text-on-primary-container px-2 py-1 rounded font-label-sm">
                        {TYPE_LABEL[q.question_type]}
                      </span>
                      <span className="bg-secondary-container text-on-secondary-container px-2 py-1 rounded font-label-sm">{q.marks} Marks</span>
                      <span className={`px-2 py-1 rounded font-label-sm ${DIFFICULTY_STYLE[q.difficulty] ?? "bg-surface-variant text-on-surface-variant"}`}>
                        {q.difficulty}
                      </span>
                    </div>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggle(i)}
                      className="h-6 w-6 text-primary rounded border-outline cursor-pointer"
                    />
                  </div>

                  <div className="font-body-lg text-on-surface mb-6">
                    <Latex text={q.question_text} />
                  </div>

                  {q.options.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6 font-body-md pl-4 border-l-2 border-surface-variant">
                      {q.options.map((opt, oi) => (
                        <div key={oi} className={`flex items-center gap-2 ${opt === q.correct_answer ? "text-primary font-bold" : ""}`}>
                          <span className="font-bold">{String.fromCharCode(65 + oi)}.</span> <Latex text={opt} />
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="perforated-divider" />

                  <details className="group mt-4">
                    <summary className="font-label-md text-secondary cursor-pointer flex items-center gap-1 select-none hover:underline">
                      <span className="material-symbols-outlined group-open:-rotate-180 transition-transform">expand_more</span>
                      Marking Scheme / Answer Key
                    </summary>
                    <div className="mt-4 pl-4 border-l-2 border-primary-container bg-surface-container-low p-4 rounded-r font-body-md text-on-surface-variant">
                      {q.evaluation_scheme.length > 0 ? (
                        q.evaluation_scheme.map((pt, pi) => (
                          <p key={pi} className={pi > 0 ? "mt-2" : ""}>
                            <span className="font-bold text-on-surface">({pt.allocated_marks} mark{pt.allocated_marks === 1 ? "" : "s"}):</span>{" "}
                            <Latex text={pt.point_text} />
                          </p>
                        ))
                      ) : (
                        <p>
                          <Latex text={q.answer} />
                        </p>
                      )}
                    </div>
                  </details>
                </div>
              );
            })}
          </div>

          <div className="lg:w-1/3 hidden lg:block relative">
            <div className="sticky top-6 bg-surface-container-low border border-outline-variant rounded-lg p-6 stamp-shadow">
              <h3 className="font-headline-md text-on-surface mb-4">Paper Summary</h3>
              <div className="flex flex-col gap-4 mb-8">
                <div className="flex justify-between items-center border-b border-outline-variant pb-2">
                  <span className="font-body-md text-on-surface-variant">Total Selected</span>
                  <span className="font-label-md text-on-surface bg-surface-variant px-2 py-1 rounded">
                    {selected.size} / {targetTotal || questions.length}
                  </span>
                </div>
                <div className="flex justify-between items-center border-b border-outline-variant pb-2">
                  <span className="font-body-md text-on-surface-variant">Total Marks</span>
                  <span className="font-label-md text-on-surface bg-primary-container text-on-primary-container px-2 py-1 rounded">
                    {totalMarks}
                  </span>
                </div>
              </div>
              {error && (
                <p className="font-label-sm text-label-sm text-error mb-3 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">error</span>
                  {error}
                </p>
              )}
              <button
                onClick={() => onFinalize([...selected])}
                disabled={isSubmitting || selected.size === 0}
                className="w-full bg-primary text-on-primary font-label-md font-bold py-4 rounded-lg flex items-center justify-center gap-2 stamp-shadow uppercase tracking-wide disabled:opacity-60"
              >
                <span className="material-symbols-outlined">check_circle</span>
                {isSubmitting ? "Finalizing…" : "Finalize Paper"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-surface border-t border-outline-variant shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
        {error && (
          <p className="font-label-sm text-label-sm text-error px-4 pt-3 flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">error</span>
            {error}
          </p>
        )}
        <div className="p-4 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="font-label-sm text-on-surface-variant uppercase">Selected</span>
            <span className="font-headline-md-mobile text-on-surface">{selected.size} <span className="text-body-md text-on-surface-variant">/ {questions.length}</span></span>
          </div>
          <button
            onClick={() => onFinalize([...selected])}
            disabled={isSubmitting || selected.size === 0}
            className="bg-primary text-on-primary px-6 py-3 rounded-lg font-label-md font-bold stamp-shadow disabled:opacity-60"
          >
            Finalize Paper
          </button>
        </div>
      </div>
    </div>
  );
}
