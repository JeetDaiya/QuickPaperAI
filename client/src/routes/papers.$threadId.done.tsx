import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DeskHeader } from "@/components/desk-header";
import { api } from "@/lib/api";

export const Route = createFileRoute("/papers/$threadId/done")({
  beforeLoad: ({ location }) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (!token) {
        throw redirect({
          to: "/login",
          search: {
            redirect: location.href,
            message: "auth_required",
          },
        });
      }
    }
  },
  head: () => ({
    meta: [
      { title: "Paper ready — QuickPaperAI" },
      {
        name: "description",
        content: "Preview and download the generated question paper.",
      },
    ],
  }),
  component: DonePage,
});

function DonePage() {
  const { threadId } = Route.useParams();
  const [cloudStatus, setCloudStatus] = useState<"idle" | "pending" | "success" | "failed">("idle");
  const [cloudError, setCloudError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["status", threadId],
    queryFn: () => api.status(threadId),
    refetchInterval: (q) =>
      q.state.data?.status === "completed" || q.state.data?.status === "failed"
        ? false
        : 1500,
  });

  const ready = data?.status === "completed";
  const failed = data?.status === "failed";
  const files = data?.status === "completed" ? data.files : null;

  async function handleSaveToCloud() {
    setCloudStatus("pending");
    setCloudError(null);
    try {
      await api.saveToCloud(threadId);
      setCloudStatus("success");
    } catch (e) {
      setCloudError(e instanceof Error ? e.message : "Failed to backup.");
      setCloudStatus("failed");
    }
  }

  return (
    <div
      className="min-h-screen surface-paper"
      style={{ ["--margin-x" as string]: "0px" }}
    >
      <DeskHeader step={4} />

      <main className="mx-auto max-w-6xl px-6 pt-20 pb-24">
        <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--graphite)]">
          Sheet 04 — Press print
        </p>
        <h1 className="mt-6 font-serif text-5xl">
          {ready ? (
            <>
              Your paper is{" "}
              <span className="underline-hand pb-2">ready</span>.
            </>
          ) : failed ? (
            <>The press jammed.</>
          ) : isLoading ? (
            "Checking the printer…"
          ) : (
            <>
              Compiling the final draft<span className="cursor-blink" />
            </>
          )}
        </h1>

        <div className="mt-12 grid gap-10 lg:grid-cols-[3fr_2fr]">
          <FoldedPreview
            ready={ready}
            url={files ? `${api.fileUrl(files.paper_pdf)}?preview=true` : null}
          />

          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-[var(--graphite)]">
              Download station
            </p>
            <ul className="mt-3 space-y-3">
              <DownloadRow
                label="Student question paper"
                hint="Printable layout · PDF"
                href={files ? api.fileUrl(files.paper_pdf) : null}
              />
              <DownloadRow
                label="Student question sheet"
                hint="Editable · DOCX"
                href={files ? api.fileUrl(files.paper_docx) : null}
              />
              <DownloadRow
                label="Answer key & marking scheme"
                hint="For the examiner · PDF"
                href={files ? api.fileUrl(files.answer_pdf) : null}
              />
            </ul>

            {ready && (
              <div className="mt-6 border border-[var(--paper-rule)] bg-[var(--paper)]/50 p-4 font-mono text-[11px] uppercase tracking-wider stamp-shadow">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="font-bold text-[var(--paper-foreground)]">Cloud vault backup</div>
                    <div className="text-[10px] text-[var(--graphite)] lowercase normal-case tracking-normal mt-0.5">
                      Uploads final compiled paper & answer key safely to cloud.
                    </div>
                  </div>
                  <button
                    disabled={cloudStatus === "pending" || cloudStatus === "success"}
                    onClick={handleSaveToCloud}
                    className={`group inline-flex items-center justify-center gap-1.5 border px-4 py-2.5 hover:stamp-shadow transition w-full sm:w-auto text-center ${cloudStatus === "success"
                        ? "border-[var(--vermillion)] bg-[var(--vermillion)] text-[var(--paper)]"
                        : "border-[var(--paper-rule)] bg-[var(--card)] text-[var(--paper-foreground)] hover:border-[var(--vermillion)]"
                      }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${cloudStatus === "success"
                          ? "bg-[var(--paper)]"
                          : cloudStatus === "pending"
                            ? "bg-[var(--vermillion)] animate-ping"
                            : "bg-[var(--graphite)]/30 group-hover:bg-[var(--vermillion)]"
                        }`}
                    />
                    {cloudStatus === "pending"
                      ? "Saving…"
                      : cloudStatus === "success"
                        ? "Saved"
                        : "Save to cloud"}
                  </button>
                </div>
                {cloudError && (
                  <p className="mt-2 normal-case tracking-normal text-[10px] text-[var(--vermillion)]">
                    Error: {cloudError}
                  </p>
                )}
              </div>
            )}

            {failed ? (
              <div className="mt-6 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)]">
                The backend reported a failure during compile. Try generating
                again from the desk.
              </div>
            ) : null}

            <div className="mt-10 border-t border-[var(--paper-rule)] pt-6 flex flex-col gap-3">
              <Link
                to="/new"
                className="group inline-flex items-center justify-center gap-2 bg-[var(--ink)] px-6 py-3.5 font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--ink-foreground)] hover:bg-[var(--vermillion)] transition text-center"
              >
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--vermillion-soft)] group-hover:bg-[var(--paper)]" />
                Set another paper
              </Link>
              <Link
                to="/"
                className="group inline-flex items-center justify-center gap-2 border border-[var(--paper-rule)] bg-[var(--card)] px-6 py-3.5 font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--paper-foreground)] hover:border-[var(--vermillion)] hover:stamp-shadow transition text-center"
              >
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--graphite)]/30 group-hover:bg-[var(--vermillion)]" />
                ← Back to desk
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function FoldedPreview({
  ready,
  url,
}: {
  ready: boolean;
  url: string | null;
}) {
  return (
    <div className="relative">
      <div
        className="relative bg-[var(--card)] shadow-[0_30px_60px_-30px_oklch(0.16_0.018_250/0.35)] border border-[var(--paper-rule)]"
        style={{ aspectRatio: "1 / 1.414" }}
      >
        <div
          aria-hidden
          className="absolute left-0 right-0 top-1/3 h-px"
          style={{
            background:
              "linear-gradient(to right, transparent, oklch(0.6 0.012 250 / 0.35), transparent)",
            boxShadow: "0 1px 0 oklch(1 0 0 / 0.6)",
          }}
        />
        {ready && url ? (
          <iframe
            src={url}
            title="Paper preview"
            className="absolute inset-0 h-full w-full"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-10 text-center">
            <div className="font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--graphite)]">
              awaiting compile
            </div>
            <div className="font-serif text-3xl text-[var(--graphite)]">
              The paper is being typeset.
            </div>
            <div
              className="h-1 w-32 overflow-hidden bg-[var(--paper-rule)]"
              aria-hidden
            >
              <div
                className="h-full w-1/2 animate-ledger"
                style={{ background: "var(--vermillion)" }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DownloadRow({
  label,
  hint,
  href,
}: {
  label: string;
  hint: string;
  href: string | null;
}) {
  const disabled = !href;
  if (disabled) {
    return (
      <li>
        <div className="flex items-center justify-between border border-dashed border-[var(--paper-rule)] bg-[var(--card)] px-4 py-4 opacity-50">
          <div>
            <div className="font-serif text-xl leading-tight">{label}</div>
            <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)]">
              {hint}
            </div>
          </div>
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--graphite)]">
            …
          </span>
        </div>
      </li>
    );
  }
  return (
    <li>
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="group flex items-center justify-between border bg-[var(--card)] px-4 py-4 transition border-[var(--paper-rule)] hover:border-[var(--vermillion)] hover:stamp-shadow"
      >
        <div>
          <div className="font-serif text-xl leading-tight">{label}</div>
          <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--graphite)]">
            {hint}
          </div>
        </div>
        <span
          aria-hidden
          className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--graphite)] group-hover:text-[var(--vermillion)]"
        >
          ↓ download
        </span>
      </a>
    </li>
  );
}
