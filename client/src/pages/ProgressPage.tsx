import { sortNatural } from "@/lib/utils";
import type { ChapterProgress, ChapterStatus } from "@/lib/api/types";

export interface ProgressPageProps {
  paperTitle: string;
  progress: Record<string, ChapterProgress>;
  onCancel: () => void;
  isCancelling: boolean;
}

const STATUS_META: Record<ChapterStatus, { label: string; icon: string; badgeClass: string }> = {
  completed: { label: "Completed", icon: "check_circle", badgeClass: "bg-surface-container-lowest border border-outline text-on-surface" },
  processing: { label: "In Progress", icon: "sync", badgeClass: "bg-surface-container border border-primary text-primary" },
  pending: { label: "Waiting", icon: "schedule", badgeClass: "bg-surface-container-lowest border border-outline-variant text-on-surface-variant" },
  failed: { label: "Failed", icon: "error", badgeClass: "bg-error-container border border-error text-on-error-container" },
};

export function ProgressPage({ paperTitle, progress, onCancel, isCancelling }: ProgressPageProps) {
  const chapters = sortNatural(Object.values(progress), (c) => c.chapter);
  const totalGenerated = chapters.reduce((sum, c) => sum + c.generated_count, 0);
  const completedCount = chapters.filter((c) => c.status === "completed").length;
  const overallPct = chapters.length ? Math.round((completedCount / chapters.length) * 100) : 0;
  const activeChapter = chapters.find((c) => c.status === "processing");

  return (
    <main className="w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-12 flex flex-col items-center">
      <div className="text-center mb-12 max-w-2xl w-full">
        <span className="material-symbols-outlined text-primary text-5xl mb-4 material-symbols-fill">auto_stories</span>
        <h1 className="font-display-lg text-display-lg text-on-surface mb-2">Generating Your Exam Paper...</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Please wait while QuickPaperAI compiles questions based on your syllabus parameters.
        </p>
      </div>

      <div className="w-full max-w-3xl bg-surface border border-outline-variant p-8 rounded stamp-shadow mb-12">
        <div className="flex justify-between items-end mb-4">
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface">Overall Progress</h2>
            <p className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mt-1">{paperTitle}</p>
          </div>
          <div className="text-right">
            <span className="font-headline-md text-headline-md text-primary font-semibold">{totalGenerated} Total Questions Generated</span>
          </div>
        </div>
        <div className="w-full h-4 bg-surface-container-high rounded-full overflow-hidden border border-outline-variant">
          <div className="h-full bg-primary rounded-full transition-all duration-1000 ease-out" style={{ width: `${overallPct}%` }} />
        </div>
        {activeChapter && (
          <div className="mt-4 flex justify-between items-center text-sm">
            <span className="font-label-md text-label-md text-on-surface-variant flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px] animate-spin">hourglass_empty</span>
              Synthesizing {activeChapter.chapter} questions…
            </span>
          </div>
        )}
      </div>

      <div className="w-full max-w-3xl space-y-4 mb-16">
        <h3 className="font-headline-md text-headline-md text-on-surface mb-6 border-b-2 border-outline-variant pb-2 inline-block">
          Chapter Processing Status
        </h3>
        {chapters.map((c) => {
          const meta = STATUS_META[c.status];
          const active = c.status === "processing";
          return (
            <div
              key={c.chapter}
              className={`bg-surface border p-6 rounded flex flex-col gap-4 relative ${
                active ? "border-primary stamp-shadow -translate-y-1 transition-transform" : "border-outline-variant stamp-shadow"
              } ${c.status === "pending" ? "opacity-70 border-dashed bg-surface-container-low" : ""}`}
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-headline-md text-[20px] leading-[28px] font-semibold text-on-surface">{c.chapter}</h4>
                <div className={`px-3 py-1 rounded-full flex items-center gap-2 ${meta.badgeClass}`}>
                  <span className="material-symbols-outlined text-[16px]">{meta.icon}</span>
                  <span className="font-label-sm text-label-sm uppercase tracking-wide font-semibold">{meta.label}</span>
                </div>
              </div>
              <p className="font-body-md text-body-md text-on-surface-variant flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">checklist</span> {c.generated_count} Questions Generated
              </p>
              <div className="w-full h-2 bg-surface-container-high rounded-full overflow-hidden border border-outline-variant">
                <div
                  className={`h-full rounded-full ${c.status === "completed" ? "bg-tertiary-container w-full" : c.status === "pending" ? "bg-outline-variant w-0" : "bg-primary"}`}
                  style={c.status === "processing" ? { width: "50%" } : undefined}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-auto pb-8 flex flex-col items-center">
        <button
          onClick={onCancel}
          disabled={isCancelling}
          className="px-6 py-3 border border-outline-variant text-on-surface-variant hover:text-error hover:border-error hover:bg-error-container font-label-md text-label-md transition-colors duration-200 flex items-center gap-2 rounded-sm bg-surface stamp-shadow disabled:opacity-60"
        >
          <span className="material-symbols-outlined text-[18px]">cancel</span>
          {isCancelling ? "Cancelling…" : "Cancel Generation"}
        </button>
      </div>
    </main>
  );
}
