import { Link } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { resolveFileUrl } from "@/lib/api/http";
import type { DraftRecord } from "@/lib/drafts";
import type { PaperHistory } from "@/lib/api/types";

export interface DashboardPageProps {
  teacherName?: string;
  schoolName?: string;
  history: PaperHistory[];
  drafts: DraftRecord[];
  notificationsEnabled: boolean;
  onToggleNotifications: (enabled: boolean) => void;
  onSignOut: () => void;
}

const DRAFT_STATUS_STYLE: Record<string, string> = {
  Ready: "bg-secondary-container text-on-secondary-container",
  "Awaiting review": "bg-primary-container text-on-primary-container",
  Generating: "bg-surface-variant text-on-surface-variant",
  Failed: "bg-error-container text-on-error-container",
};

export function DashboardPage({
  teacherName = "there",
  schoolName,
  history,
  drafts,
  notificationsEnabled,
  onToggleNotifications,
  onSignOut,
}: DashboardPageProps) {
  return (
    <AppShell active="dashboard" schoolName={schoolName} onSignOut={onSignOut}>
      <div className="p-margin-mobile md:p-margin-desktop flex-1">
        <div className="mb-12">
          <h1 className="font-display-lg text-display-lg text-on-surface mb-2">Welcome back, {teacherName}</h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">Ready to compile the next assessment?</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Link
            to="/generate/setup"
            className="md:col-span-2 bg-surface-container-lowest border border-outline-variant rounded-xl p-8 shadow-stamp flex flex-col justify-between relative overflow-hidden group cursor-pointer hover:border-primary transition-colors"
          >
            <div>
              <div className="w-12 h-12 bg-primary-container text-primary rounded flex items-center justify-center mb-6">
                <span className="material-symbols-outlined text-2xl material-symbols-fill">post_add</span>
              </div>
              <h2 className="font-headline-md text-headline-md text-on-surface mb-2">New Exam Paper</h2>
              <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
                Launch the generator to create a customized assessment tailored to your curriculum.
              </p>
            </div>
            <div className="mt-8 flex items-center text-primary font-label-md text-label-md font-bold group-hover:translate-x-2 transition-transform">
              Start Generator <span className="material-symbols-outlined ml-2">arrow_forward</span>
            </div>
          </Link>

          <div className="bg-surface-container-low border border-outline-variant rounded-xl p-6 shadow-sheet flex flex-col justify-between">
            <div>
              <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-4">Cloud Vault</h3>
              <div className="text-4xl font-display-lg text-on-surface mb-1">{history.length}</div>
              <p className="font-body-md text-body-md text-on-surface-variant">Papers saved</p>
            </div>
          </div>
        </div>

        {drafts.length > 0 && (
          <div className="mb-12">
            <div className="mb-4 flex justify-between items-end border-b border-outline-variant pb-2">
              <div>
                <h2 className="font-headline-md text-headline-md text-on-surface">Recent Drafts</h2>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  Pick up any paper you started — tracked on this device, not yet saved to the Cloud Vault.
                </p>
              </div>
            </div>
            <div className="bg-surface-container-lowest border border-outline-variant rounded-lg divide-y divide-outline-variant overflow-hidden">
              {drafts.map((d) => (
                <Link
                  key={d.threadId}
                  to="/generate/$threadId"
                  params={{ threadId: d.threadId }}
                  className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-surface-container-low transition-colors"
                >
                  <div className="min-w-0">
                    <div className="font-label-md text-label-md font-bold text-on-surface truncate">
                      {d.institution || "Untitled institution"}
                    </div>
                    <div className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mt-1 flex items-center gap-2">
                      <span>
                        {d.subject} · {d.standard}
                      </span>
                      {d.status && (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${DRAFT_STATUS_STYLE[d.status] ?? "bg-surface-variant text-on-surface-variant"}`}>
                          {d.status}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="shrink-0 flex items-center gap-1 font-label-sm text-label-sm text-on-surface-variant">
                    {new Date(d.createdAt).toLocaleDateString()}
                    <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Notification Settings */}
        <div className="mt-12 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 md:p-8 shadow-sheet relative overflow-hidden mb-12">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-outline-variant">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-surface-variant text-primary flex items-center justify-center">
                <span className="material-symbols-outlined text-2xl">notifications_active</span>
              </div>
              <div>
                <h2 className="font-headline-md text-headline-md text-on-surface">Notifications</h2>
                <p className="font-body-md text-body-md text-on-surface-variant">Manage exam generation alerts</p>
              </div>
            </div>
            <div className="flex items-center gap-2 bg-surface-container-low border border-outline-variant px-3 py-1.5 rounded-full">
              <span className={`w-2 h-2 rounded-full ${notificationsEnabled ? "bg-secondary animate-pulse" : "bg-outline-variant"}`} />
              <span className="font-label-sm text-label-sm text-on-surface-variant font-medium">
                {notificationsEnabled ? "Enabled on this device" : "Disabled on this device"}
              </span>
            </div>
          </div>
          <div className="pt-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="max-w-xl">
                <span className="font-label-md text-label-md font-bold text-on-surface">
                  Notify me when a paper finishes generating
                </span>
                <p className="font-body-md text-body-md text-on-surface-variant mt-1">
                  Receive a push notification as soon as your draft is ready for review.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={notificationsEnabled}
                  onChange={(e) => onToggleNotifications(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-12 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-outline-variant after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-container" />
              </label>
            </div>
          </div>
        </div>

        <div className="mb-8 flex justify-between items-end border-b border-outline-variant pb-2">
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface">Cloud Vault</h2>
            <p className="font-body-md text-body-md text-on-surface-variant">Saved papers</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {history.map((paper) => (
            <div
              key={paper.id}
              className="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 shadow-sheet hover:shadow-stamp transition-shadow flex flex-col relative group"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="bg-surface-variant text-on-surface-variant p-2 rounded">
                  <span className="material-symbols-outlined">menu_book</span>
                </div>
              </div>
              <h3 className="font-label-md text-label-md font-bold text-on-surface mb-1">{paper.institution_name}</h3>
              <p className="font-label-sm text-label-sm text-on-surface-variant mb-4">
                {paper.subject} · Standard {paper.standard}
              </p>
              <div className="mt-auto pt-4 border-t border-outline-variant flex justify-between items-center text-on-surface-variant">
                <span className="font-label-sm text-label-sm">{new Date(paper.created_at).toLocaleDateString()}</span>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <a
                    href={resolveFileUrl(paper.paper_pdf) + "&preview=true"}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:text-primary transition-colors"
                    title="Preview paper PDF"
                    aria-label="Preview paper PDF"
                  >
                    <span className="material-symbols-outlined text-[20px]">visibility</span>
                  </a>
                  <a
                    href={resolveFileUrl(paper.paper_pdf)}
                    className="hover:text-primary transition-colors"
                    title="Download paper PDF"
                    aria-label="Download paper PDF"
                  >
                    <span className="material-symbols-outlined text-[20px]">picture_as_pdf</span>
                  </a>
                  <a
                    href={resolveFileUrl(paper.paper_docx)}
                    className="hover:text-primary transition-colors"
                    title="Download editable DOCX"
                    aria-label="Download editable DOCX"
                  >
                    <span className="material-symbols-outlined text-[20px]">description</span>
                  </a>
                  <a
                    href={resolveFileUrl(paper.answer_pdf)}
                    className="hover:text-primary transition-colors"
                    title="Download answer key PDF"
                    aria-label="Download answer key PDF"
                  >
                    <span className="material-symbols-outlined text-[20px]">fact_check</span>
                  </a>
                </div>
              </div>
            </div>
          ))}
          <Link
            to="/generate/setup"
            className="bg-surface-container-low border border-dashed border-outline-variant rounded-lg p-5 hover:bg-surface-variant transition-colors flex flex-col items-center justify-center text-center cursor-pointer min-h-[200px]"
          >
            <div className="bg-primary-container text-primary p-3 rounded-full mb-3">
              <span className="material-symbols-outlined">add</span>
            </div>
            <h3 className="font-label-md text-label-md font-bold text-on-surface">Generate Paper</h3>
            <p className="font-label-sm text-label-sm text-on-surface-variant mt-1">Start a new draft</p>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
