import { useState } from "react";
import { Link } from "@tanstack/react-router";

export interface DownloadsPageProps {
  paperPdfUrl: string;
  paperDocxUrl: string;
  answerPdfUrl: string;
  onSaveToCloud: () => void;
  isSaving: boolean;
  saved: boolean;
}

export function DownloadsPage({ paperPdfUrl, paperDocxUrl, answerPdfUrl, onSaveToCloud, isSaving, saved }: DownloadsPageProps) {
  const [previewing, setPreviewing] = useState<"paper" | "answer">("paper");
  const previewUrl = previewing === "paper" ? paperPdfUrl : answerPdfUrl;
  return (
    <div className="text-on-surface min-h-screen flex flex-col font-body-md">
      <main className="flex-grow flex flex-col md:flex-row max-w-container-max mx-auto w-full px-margin-mobile md:px-margin-desktop py-8 md:py-12 gap-gutter">
        <div className="w-full md:w-5/12 flex flex-col gap-8">
          <section className="flex flex-col gap-4">
            <div className="flex items-center gap-3 text-secondary">
              <span className="material-symbols-outlined material-symbols-fill" style={{ fontSize: 32 }}>task_alt</span>
              <span className="font-label-md text-label-md uppercase tracking-wider font-bold">Process Complete</span>
            </div>
            <h1 className="font-display-lg text-display-lg text-on-surface">Paper Compiled Successfully.</h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">
              Your assessment document is ready for distribution.
            </p>
          </section>

          <section className="bg-surface-container-lowest p-6 rounded-lg shadow-sheet border border-outline-variant flex flex-col gap-4">
            <h2 className="font-headline-md text-headline-md-mobile md:text-headline-md mb-2">Final Documents</h2>
            <a
              href={paperPdfUrl}
              className="w-full bg-primary-container text-on-primary-container font-label-md text-label-md py-4 px-6 rounded hover:bg-primary transition-colors duration-200 flex items-center justify-between group"
            >
              <span className="flex flex-col items-start gap-1">
                <span className="font-bold text-base">Download PDF (Print-Ready)</span>
                <span className="opacity-80 text-xs font-normal">Standard A4 Layout</span>
              </span>
              <span className="material-symbols-outlined group-hover:translate-y-1 transition-transform duration-200">download</span>
            </a>
            <a
              href={paperDocxUrl}
              className="w-full bg-transparent border border-secondary text-secondary font-label-md text-label-md py-4 px-6 rounded hover:bg-surface-container-low transition-colors duration-200 flex items-center justify-between group"
            >
              <span className="flex flex-col items-start gap-1">
                <span className="font-bold text-base">Download DOCX (Editable)</span>
                <span className="opacity-80 text-xs font-normal">Microsoft Word format for final tweaks</span>
              </span>
              <span className="material-symbols-outlined group-hover:translate-y-1 transition-transform duration-200">download</span>
            </a>
            <a
              href={answerPdfUrl}
              className="w-full bg-transparent border border-outline-variant text-on-surface font-label-md text-label-md py-4 px-6 rounded hover:bg-surface-container-low transition-colors duration-200 flex items-center justify-between group"
            >
              <span className="flex flex-col items-start gap-1">
                <span className="font-bold text-base flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[18px]">fact_check</span>
                  Download Answer Key (PDF)
                </span>
                <span className="opacity-80 text-xs font-normal">For examiner use — not for distribution to students</span>
              </span>
              <span className="material-symbols-outlined group-hover:translate-y-1 transition-transform duration-200">download</span>
            </a>
          </section>

          <section className="bg-surface-container-low p-6 rounded-lg border border-outline-variant flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">cloud_upload</span>
              <h3 className="font-label-md text-label-md font-bold uppercase tracking-wider text-secondary">Save to Cloud Vault</h3>
            </div>
            <p className="font-body-md text-body-md text-on-surface-variant text-sm">
              Keep this paper in your history for future access and re-download.
            </p>
            <button
              onClick={onSaveToCloud}
              disabled={isSaving || saved}
              className="w-full bg-secondary text-on-secondary font-label-md text-label-md py-3 px-6 rounded shadow-sm hover:bg-secondary-container hover:text-on-secondary-container transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">{saved ? "check_circle" : "cloud_upload"}</span>
              {saved ? "Saved to Cloud Vault" : isSaving ? "Saving…" : "Save to Cloud Vault"}
            </button>
          </section>

          <Link
            to="/generate/setup"
            className="text-secondary font-label-md text-label-md font-bold py-3 px-6 hover:underline flex items-center gap-2 w-max self-start"
          >
            <span className="material-symbols-outlined">add_circle</span>
            Start New Paper
          </Link>
        </div>

        <div className="w-full md:w-7/12 flex flex-col items-center gap-4">
          <div className="flex gap-2 self-center">
            <button
              type="button"
              onClick={() => setPreviewing("paper")}
              className={`px-4 py-1.5 rounded-full font-label-sm text-label-sm font-semibold border transition-colors ${
                previewing === "paper" ? "bg-primary-container text-on-primary-container border-primary" : "bg-surface-container-lowest text-on-surface-variant border-outline-variant"
              }`}
            >
              Exam Paper
            </button>
            <button
              type="button"
              onClick={() => setPreviewing("answer")}
              className={`px-4 py-1.5 rounded-full font-label-sm text-label-sm font-semibold border transition-colors ${
                previewing === "answer" ? "bg-primary-container text-on-primary-container border-primary" : "bg-surface-container-lowest text-on-surface-variant border-outline-variant"
              }`}
            >
              Answer Key
            </button>
          </div>
          <div className="bg-surface-container-lowest w-full max-w-[600px] aspect-[1/1.414] shadow-sheet border border-outline-variant rounded p-8 md:p-12 flex flex-col relative">
            <iframe title={`${previewing === "paper" ? "Paper" : "Answer key"} preview`} src={`${previewUrl}&preview=true`} className="w-full h-full border-0" />
          </div>
        </div>
      </main>

      <footer className="bg-surface-container-lowest border-t border-dashed border-outline-variant w-full flex flex-col items-center justify-center gap-4 px-margin-desktop py-8 mt-auto">
        <div className="font-label-md text-label-md font-bold text-on-surface">QuickPaperAI</div>
        <p className="text-on-surface-variant font-label-sm text-label-sm opacity-70">© 2024 QuickPaperAI Academic Systems</p>
      </footer>
    </div>
  );
}
