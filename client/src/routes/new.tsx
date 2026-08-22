import { createFileRoute, useNavigate, redirect } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { DeskHeader } from "@/components/desk-header";
import { api } from "@/lib/api";
import { upsertDraft, setActiveThread } from "@/lib/drafts";
import {
  MODE_ALLOWED,
} from "@/lib/paper-config";
import { useFCMNotification } from "@/hooks/useFCMNotification";
import type {
  Difficulty,
  DifficultyDistribution,
  GenerateRequest,
  PaperTypeMode,
  QuestionType,
} from "@/lib/types";
import { DIFFICULTY_PRESETS } from "@/lib/types";

function getUnsavedStateKey(): string {
  if (typeof window === "undefined") return "qpa.unsaved_new_paper_state";
  const token = localStorage.getItem("token");
  if (!token) return "qpa.unsaved_new_paper_state";
  try {
    const parts = token.split(".");
    if (parts.length === 3) {
      const base64Url = parts[1];
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = decodeURIComponent(
        window.atob(base64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join("")
      );
      const payload = JSON.parse(jsonPayload);
      if (payload.sub) {
        return `qpa.unsaved_new_paper_state:${payload.sub}`;
      }
    }
  } catch {}
  return "qpa.unsaved_new_paper_state";
}

export const Route = createFileRoute("/new")({
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
      { title: "New Paper — QuickPaperAI" },
      {
        name: "description",
        content:
          "Configure the syllabus, scheme, and counts for a new question paper.",
      },
    ],
  }),
  component: NewPaper,
});

const DIFFICULTIES: Difficulty[] = ["Easy", "Balanced", "Hard"];
const MODES: PaperTypeMode[] = [
  "Balanced Standard Mode",
  "MCQ-Only Mode",
  "Objective-Only Mode",
];

function NewPaper() {
  const navigate = useNavigate();
  const fcm = useFCMNotification();
  const [institutionName, setInstitutionName] = useState("");

  const [subject, setSubject] = useState<string>("");
  const [standard, setStandard] = useState<string>("");
  const [chapters, setChapters] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<Difficulty>("Balanced");
  const [difficultyDistribution, setDifficultyDistribution] = useState<DifficultyDistribution>({
    easy: 20,
    medium: 50,
    hard: 30,
  });
  const [isCustomDifficulty, setIsCustomDifficulty] = useState(false);

  const [mode, setMode] = useState<PaperTypeMode>("Balanced Standard Mode");
  const [allowedTypes, setAllowedTypes] = useState<QuestionType[]>(
    MODE_ALLOWED["Balanced Standard Mode"],
  );
  const [objectiveCount, setObjectiveCount] = useState(5);
  const [subjectiveCount, setSubjectiveCount] = useState(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [unsavedState, setUnsavedState] = useState<any>(null);
  const [isRestoredOrStarted, setIsRestoredOrStarted] = useState(false);

  const handleSelectPreset = (key: string) => {
    const preset = DIFFICULTY_PRESETS[key];
    if (preset) {
      setDifficulty(preset.modeLabel);
      setDifficultyDistribution(preset.distribution);
      setIsCustomDifficulty(false);
    }
  };

  const handleCustomDistChange = (field: keyof DifficultyDistribution, val: number) => {
    const clamped = Math.max(0, Math.min(100, val || 0));
    setDifficultyDistribution((prev) => ({
      ...prev,
      [field]: clamped,
    }));
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(getUnsavedStateKey());
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (parsed.institutionName || parsed.chapters?.length > 0) {
            setUnsavedState(parsed);
          } else {
            setIsRestoredOrStarted(true);
          }
        } catch (e) {
          setIsRestoredOrStarted(true);
        }
      } else {
        setIsRestoredOrStarted(true);
      }
    }
  }, []);

  useEffect(() => {
    if (isRestoredOrStarted && typeof window !== "undefined") {
      const stateObj = {
        institutionName,
        subject,
        standard,
        chapters,
        difficulty,
        difficultyDistribution,
        mode,
        allowedTypes,
        objectiveCount,
        subjectiveCount,
      };
      if (institutionName.trim() || chapters.length > 0) {
        localStorage.setItem(getUnsavedStateKey(), JSON.stringify(stateObj));
      } else {
        localStorage.removeItem(getUnsavedStateKey());
      }
    }
  }, [
    isRestoredOrStarted,
    institutionName,
    subject,
    standard,
    chapters,
    difficulty,
    difficultyDistribution,
    mode,
    allowedTypes,
    objectiveCount,
    subjectiveCount,
  ]);

  const handleRestore = () => {
    if (unsavedState) {
      setInstitutionName(unsavedState.institutionName || "");
      setSubject(unsavedState.subject || "");
      setStandard(unsavedState.standard || "");
      setChapters(unsavedState.chapters || []);
      setDifficulty(unsavedState.difficulty || "Balanced");
      if (unsavedState.difficultyDistribution) {
        setDifficultyDistribution(unsavedState.difficultyDistribution);
      } else if (unsavedState.difficulty) {
        const key = unsavedState.difficulty.toUpperCase();
        const mapped = DIFFICULTY_PRESETS[key]?.distribution || { easy: 20, medium: 50, hard: 30 };
        setDifficultyDistribution(mapped);
      }
      setMode(unsavedState.mode || "Balanced Standard Mode");
      setAllowedTypes(
        unsavedState.allowedTypes ||
          MODE_ALLOWED[(unsavedState.mode as PaperTypeMode) || "Balanced Standard Mode"]
      );
      setObjectiveCount(unsavedState.objectiveCount ?? 5);
      setSubjectiveCount(unsavedState.subjectiveCount ?? 3);
      setUnsavedState(null);
      setIsRestoredOrStarted(true);
    }
  };

  const handleDiscard = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(getUnsavedStateKey());
    }
    setUnsavedState(null);
    setIsRestoredOrStarted(true);
  };

  // Fetch chapters and syllabus mapping directly from database chunks
  const { data: dbMetadata, isLoading: loadingMetadata } = useQuery({
    queryKey: ["dbChapters"],
    queryFn: () => api.getChapters(),
  });

  const subjects = useMemo(() => {
    if (!dbMetadata?.chapters || dbMetadata.chapters.length === 0) {
      return [];
    }
    const set = new Set(dbMetadata.chapters.map((c) => c.subject));
    return Array.from(set).sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }),
    );
  }, [dbMetadata]);

  const standards = useMemo(() => {
    if (!dbMetadata?.chapters || dbMetadata.chapters.length === 0) {
      return [];
    }
    const set = new Set(dbMetadata.chapters.map((c) => c.standard));
    return Array.from(set).sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }),
    );
  }, [dbMetadata]);

  // Set default selection values once loaded, with self-healing to align on schema changes
  useEffect(() => {
    if (subjects.length > 0 && (!subject || !subjects.includes(subject))) {
      const defaultSub = subjects.includes("science") ? "science" : subjects[0];
      setSubject(defaultSub);
    }
  }, [subjects, subject]);

  useEffect(() => {
    if (standards.length > 0 && (!standard || !standards.includes(standard))) {
      const defaultStd = standards.includes("10") ? "10" : standards[0];
      setStandard(defaultStd);
    }
  }, [standards, standard]);

  const chapterList = useMemo(() => {
    if (!dbMetadata?.chapters || !subject || !standard) return [];
    // Get unique chapter names matching selected subject and standard
    const names = dbMetadata.chapters
      .filter((c) => c.subject === subject && c.standard === standard)
      .map((c) => c.chapter_name);
    return Array.from(new Set(names)).sort((a, b) =>
      a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }),
    );
  }, [dbMetadata, subject, standard]);

  const allowedForMode = MODE_ALLOWED[mode];
  const modeLocksAllowed = mode !== "Balanced Standard Mode";

  function toggle<T>(arr: T[], v: T): T[] {
    return arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v];
  }

  function onChangeMode(next: PaperTypeMode) {
    setMode(next);
    setAllowedTypes(MODE_ALLOWED[next]);
    if (next === "Objective-Only Mode" || next === "MCQ-Only Mode") {
      setSubjectiveCount(0);
      if (objectiveCount === 0) {
        setObjectiveCount(5);
      }
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!institutionName.trim()) return setError("Institution name is required.");
    if (chapters.length === 0) return setError("Pick at least one chapter.");
    if (allowedTypes.length === 0)
      return setError("At least one allowed question type is required.");
    const totalDist =
      difficultyDistribution.easy +
      difficultyDistribution.medium +
      difficultyDistribution.hard;
    if (totalDist !== 100) {
      return setError(
        `Difficulty percentages must sum to 100% (currently ${totalDist}%).`
      );
    }

    const payload: GenerateRequest = {
      institution_name: institutionName.trim(),
      subject,
      standard,
      chapters,
      difficulty,
      difficulty_distribution: difficultyDistribution,
      paper_type_mode: mode,
      allowed_types: allowedTypes,
      objective_count: objectiveCount,
      subjective_count: subjectiveCount,
    };

    setSubmitting(true);
    try {
      const { thread_id } = await api.generate(payload);
      if (typeof window !== "undefined") {
        localStorage.removeItem(getUnsavedStateKey());
      }
      upsertDraft({
        threadId: thread_id,
        institution: payload.institution_name,
        subject,
        standard,
        createdAt: Date.now(),
        status: "Generating",
      });
      setActiveThread(thread_id);
      navigate({
        to: "/papers/$threadId/progress",
        params: { threadId: thread_id },
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not reach the backend. Is FastAPI running on localhost:8000?",
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen surface-paper relative">
      {/* Floating Top-Right Toast Notification for Sum Enforcement */}
      {(() => {
        const currentSum =
          difficultyDistribution.easy +
          difficultyDistribution.medium +
          difficultyDistribution.hard;
        if (currentSum !== 100 && (isCustomDifficulty || (error && error.includes("100%")))) {
          return (
            <div className="fixed top-6 right-6 z-50 flex items-start gap-3.5 border border-[var(--vermillion)] bg-[var(--paper)] p-4 shadow-2xl rounded-sm border-l-4 border-l-[var(--vermillion)] max-w-sm">
              <span className="text-xl shrink-0">⚠️</span>
              <div className="flex-1 min-w-0">
                <div className="font-mono text-xs uppercase tracking-[0.16em] font-bold text-[var(--vermillion)]">
                  Sum Constraint Error
                </div>
                <p className="mt-1 font-mono text-xs text-[var(--ink)] leading-snug">
                  Percentages must sum to 100% (currently{" "}
                  <span className="font-bold text-[var(--vermillion)]">{currentSum}%</span>).
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  const diff = 100 - currentSum;
                  setDifficultyDistribution((prev) => ({
                    ...prev,
                    medium: Math.max(0, prev.medium + diff),
                  }));
                }}
                className="shrink-0 font-mono text-[10px] uppercase font-bold text-[var(--vermillion)] hover:bg-[var(--vermillion)] hover:text-[var(--paper)] transition cursor-pointer bg-[var(--vermillion)]/10 px-2.5 py-1 rounded-2xs border border-[var(--vermillion)]/30"
              >
                Auto-fix
              </button>
            </div>
          );
        }
        return null;
      })()}

      <DeskHeader step={1} />

      <main className="mx-auto max-w-4xl px-6 pt-20 pb-24 md:pl-28">
        <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--graphite)]">
          Sheet 01 — Request
        </p>
        <h1 className="mt-6 font-serif text-5xl">Set the scheme.</h1>
        <p className="mt-6 max-w-xl text-[var(--graphite)]">
          Fill the slip the way an examiner would on a Monday morning. Every
          field maps to a backend constraint — invalid combinations are
          disabled here so nothing reaches the generator wrong.
        </p>

        {unsavedState && (
          <div className="mt-8 border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-4 font-mono text-xs text-[var(--vermillion)] flex flex-wrap justify-between items-center gap-4 stamp-shadow animate-shuffle">
            <div>
              <span className="font-bold mr-1">📝 Recovered Paper Plan:</span>
              We recovered an unfinished setup for "{unsavedState.institutionName || "Untitled"}".
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleRestore}
                className="underline font-bold cursor-pointer bg-transparent border-none text-[var(--vermillion)] p-0 hover:text-[var(--ink)] transition-colors"
              >
                Restore settings
              </button>
              <span className="opacity-50">·</span>
              <button
                type="button"
                onClick={handleDiscard}
                className="underline cursor-pointer bg-transparent border-none text-[var(--graphite)] p-0 hover:text-[var(--ink)] transition-colors"
              >
                Discard
              </button>
            </div>
          </div>
        )}

        {/* FCM Push Notification Banner & Settings */}
        {fcm.permissionStatus !== "granted" ? (
          <div className="mt-6 border border-[var(--paper-rule)] bg-[var(--card)] p-4 font-mono text-xs text-[var(--paper-foreground)] flex flex-wrap items-center justify-between gap-4 stamp-shadow">
            <div className="flex items-center gap-2">
              <span className="text-base">📲</span>
              <div>
                <span className="font-bold text-[var(--paper-foreground)]">Enable Push Notifications:</span> Get instant alerts on your device when your question papers complete generation.
              </div>
            </div>
            <button
              type="button"
              disabled={fcm.loading}
              onClick={() => { void fcm.requestPermission(); }}
              className="group inline-flex items-center gap-2 rounded-sm bg-[var(--ink)] px-4 py-2 text-[11px] uppercase tracking-wider text-[var(--ink-foreground)] transition hover:bg-[var(--vermillion)] cursor-pointer disabled:opacity-50"
            >
              <span>{fcm.loading ? "Requesting…" : "Enable Notifications"}</span>
              <span aria-hidden>→</span>
            </button>
          </div>
        ) : (
          <div className="mt-6 border border-[var(--paper-rule)] bg-[var(--card)]/60 px-4 py-3 font-mono text-xs text-[var(--graphite)] flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-emerald-600 font-bold">✓</span>
              <span>Push notifications active for this device</span>
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none text-[11px]">
              <span>Alerts:</span>
              <input
                type="checkbox"
                checked={fcm.notificationsEnabled}
                onChange={(e) => fcm.toggleNotifications(e.target.checked)}
                className="cursor-pointer accent-[var(--vermillion)]"
              />
              <span className="font-bold text-[var(--paper-foreground)]">
                {fcm.notificationsEnabled ? "ON" : "OFF"}
              </span>
            </label>
          </div>
        )}

        <form onSubmit={onSubmit} className="mt-10 space-y-10">
          <FieldRow n={1} label="Institution">
            <input
              required
              value={institutionName}
              onChange={(e) => setInstitutionName(e.target.value)}
              placeholder="St. Xavier's High School"
              className="w-full border-b border-[var(--paper-rule)] bg-transparent pb-2 font-serif text-2xl outline-none focus:border-[var(--vermillion)]"
            />
          </FieldRow>

          <FieldRow n={2} label="Subject & Standard">
            {loadingMetadata ? (
              <span className="font-mono text-xs uppercase tracking-[0.18em] opacity-60">
                Loading database syllabus…
              </span>
            ) : (
              <div className="flex flex-wrap gap-4">
                <Select
                  value={subject}
                  onChange={(v) => {
                    setSubject(v);
                    setChapters([]);
                  }}
                  options={subjects}
                />
                <Select
                  value={standard}
                  onChange={setStandard}
                  options={standards}
                />
              </div>
            )}
          </FieldRow>

          <FieldRow n={3} label="Chapters">
            {loadingMetadata ? (
              <span className="font-mono text-xs uppercase tracking-[0.18em] opacity-60">
                Syncing chapters ledger…
              </span>
            ) : chapterList.length === 0 ? (
              <p className="text-sm text-[var(--graphite)]">
                No chapters cached in database chunks for "{subject}" & "{standard}".
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {chapterList.map((c) => {
                  const on = chapters.includes(c);
                  return (
                    <label
                      key={c}
                      className={`flex cursor-pointer items-start gap-3 border bg-[var(--card)] px-3 py-2.5 text-sm transition ${
                        on
                          ? "border-[var(--vermillion)] stamp-shadow"
                          : "border-[var(--paper-rule)] hover:border-[var(--graphite)]"
                      }`}
                    >
                      <span
                        aria-hidden
                        className={`mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center border ${
                          on
                            ? "border-[var(--vermillion)] bg-[var(--vermillion)] text-[var(--paper)]"
                            : "border-[var(--graphite)]"
                        }`}
                      >
                        {on ? "✓" : ""}
                      </span>
                      <span>{c}</span>
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={on}
                        onChange={() => setChapters(toggle(chapters, c))}
                      />
                    </label>
                  );
                })}
              </div>
            )}
          </FieldRow>

          <FieldRow n={4} label="Difficulty Blueprint">
            <div className="space-y-4">
              {/* Stacked Tri-Color Distribution Progress Bar */}
              <div className="border border-[var(--paper-rule)] bg-[var(--card)] p-3 rounded-sm stamp-shadow">
                <div className="flex h-3 w-full rounded-2xs overflow-hidden bg-[var(--paper)]">
                  <div
                    style={{ width: `${Math.max(0, Math.min(100, difficultyDistribution.easy))}%` }}
                    className="bg-emerald-600 transition-all duration-300"
                    title={`Easy: ${difficultyDistribution.easy}%`}
                  />
                  <div
                    style={{ width: `${Math.max(0, Math.min(100, difficultyDistribution.medium))}%` }}
                    className="bg-[#005FAF] transition-all duration-300"
                    title={`Medium: ${difficultyDistribution.medium}%`}
                  />
                  <div
                    style={{ width: `${Math.max(0, Math.min(100, difficultyDistribution.hard))}%` }}
                    className="bg-[#AF101A] transition-all duration-300"
                    title={`Hard: ${difficultyDistribution.hard}%`}
                  />
                </div>
                <div className="mt-2 flex flex-wrap justify-between px-1 font-mono text-[10px] uppercase tracking-[0.14em]">
                  <span className="text-emerald-700 font-bold">🟢 Easy {difficultyDistribution.easy}%</span>
                  <span className="text-[#005FAF] font-bold">🔵 Medium {difficultyDistribution.medium}%</span>
                  <span className="text-[#AF101A] font-bold">🔴 Hard {difficultyDistribution.hard}%</span>
                  <span className={`ml-auto ${difficultyDistribution.easy + difficultyDistribution.medium + difficultyDistribution.hard === 100 ? "text-[var(--graphite)]" : "text-[var(--vermillion)] font-bold"}`}>
                    Total: {difficultyDistribution.easy + difficultyDistribution.medium + difficultyDistribution.hard}%
                  </span>
                </div>
              </div>

              {/* Preset Cards Grid (4 Equal Tiles) */}
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
                {Object.entries(DIFFICULTY_PRESETS).map(([key, preset]) => {
                  const isSelected =
                    !isCustomDifficulty &&
                    difficultyDistribution.easy === preset.distribution.easy &&
                    difficultyDistribution.medium === preset.distribution.medium &&
                    difficultyDistribution.hard === preset.distribution.hard;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => handleSelectPreset(key)}
                      className={`flex flex-col justify-between text-left border p-3.5 transition rounded-sm cursor-pointer ${
                        isSelected
                          ? "border-[var(--ink)] bg-[var(--card)] shadow-xs ring-1 ring-[var(--ink)]"
                          : "border-[var(--paper-rule)] bg-[var(--surface)] hover:border-[var(--graphite)]"
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="font-serif font-bold text-base">{preset.label}</span>
                          {isSelected && <span className="font-mono text-xs text-[var(--vermillion)] font-bold">✓</span>}
                        </div>
                        <p className="mt-1 font-mono text-[10px] text-[var(--graphite)] leading-tight">
                          {preset.description}
                        </p>
                      </div>
                      <div className="mt-3 pt-2 border-t border-[var(--paper-rule)] font-mono text-[10px] text-[var(--paper-foreground)]">
                        {preset.distribution.easy}%E · {preset.distribution.medium}%M · {preset.distribution.hard}%H
                      </div>
                    </button>
                  );
                })}

                {/* 4th Card: Custom Allocation Tile */}
                <button
                  type="button"
                  onClick={() => setIsCustomDifficulty(true)}
                  className={`flex flex-col justify-between text-left border p-3.5 transition rounded-sm cursor-pointer ${
                    isCustomDifficulty
                      ? "border-[var(--ink)] bg-[var(--card)] shadow-xs ring-1 ring-[var(--ink)]"
                      : "border-[var(--paper-rule)] bg-[var(--surface)] hover:border-[var(--graphite)]"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-serif font-bold text-base">⚙️ Custom %</span>
                      {isCustomDifficulty && <span className="font-mono text-xs text-[var(--vermillion)] font-bold">✓</span>}
                    </div>
                    <p className="mt-1 font-mono text-[10px] text-[var(--graphite)] leading-tight">
                      Specify exact custom percentages
                    </p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-[var(--paper-rule)] font-mono text-[10px] text-[var(--vermillion)] font-bold">
                    Interactive Sliders
                  </div>
                </button>
              </div>

              {/* Custom Sliders & Inputs Panel */}
              {isCustomDifficulty && (
                <div className="border border-[var(--ink)] bg-[var(--card)] p-5 rounded-sm space-y-4 stamp-shadow animate-shuffle">
                  <div className="flex items-center justify-between border-b border-[var(--paper-rule)] pb-2">
                    <div className="font-mono text-[11px] uppercase tracking-[0.18em] font-bold text-[var(--ink)]">
                      ⚙️ Custom Cognitive Percentages
                    </div>
                    <div className="font-mono text-[10px] text-[var(--graphite)]">
                      Constraint: Must equal <span className="font-bold text-[var(--ink)]">100%</span>
                    </div>
                  </div>

                  <div className="grid gap-5 sm:grid-cols-3">
                    {/* Easy Slider */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between font-mono text-[10px] uppercase font-bold text-emerald-700">
                        <span>🟢 Easy</span>
                        <span>{difficultyDistribution.easy}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={difficultyDistribution.easy}
                        onChange={(e) => handleCustomDistChange("easy", parseInt(e.target.value) || 0)}
                        className="w-full accent-emerald-600 cursor-pointer"
                      />
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={difficultyDistribution.easy}
                        onChange={(e) => handleCustomDistChange("easy", parseInt(e.target.value) || 0)}
                        className="w-full border border-[var(--paper-rule)] bg-[var(--paper)] p-2 font-mono text-xs outline-none focus:border-emerald-600 text-center"
                      />
                    </div>

                    {/* Medium Slider */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between font-mono text-[10px] uppercase font-bold text-[#005FAF]">
                        <span>🔵 Medium</span>
                        <span>{difficultyDistribution.medium}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={difficultyDistribution.medium}
                        onChange={(e) => handleCustomDistChange("medium", parseInt(e.target.value) || 0)}
                        className="w-full accent-[#005FAF] cursor-pointer"
                      />
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={difficultyDistribution.medium}
                        onChange={(e) => handleCustomDistChange("medium", parseInt(e.target.value) || 0)}
                        className="w-full border border-[var(--paper-rule)] bg-[var(--paper)] p-2 font-mono text-xs outline-none focus:border-[#005FAF] text-center"
                      />
                    </div>

                    {/* Hard Slider */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between font-mono text-[10px] uppercase font-bold text-[#AF101A]">
                        <span>🔴 Hard</span>
                        <span>{difficultyDistribution.hard}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={difficultyDistribution.hard}
                        onChange={(e) => handleCustomDistChange("hard", parseInt(e.target.value) || 0)}
                        className="w-full accent-[#AF101A] cursor-pointer"
                      />
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={difficultyDistribution.hard}
                        onChange={(e) => handleCustomDistChange("hard", parseInt(e.target.value) || 0)}
                        className="w-full border border-[var(--paper-rule)] bg-[var(--paper)] p-2 font-mono text-xs outline-none focus:border-[#AF101A] text-center"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </FieldRow>

          <FieldRow n={5} label="Paper type mode">
            <Segmented value={mode} options={MODES} onChange={onChangeMode} />
            <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--graphite)]">
              {mode === "MCQ-Only Mode"
                ? "Allowed types locked to MCQ."
                : mode === "Objective-Only Mode"
                  ? "Allowed types locked to objective set. Subjective count forced to 0."
                  : "All question types available."}
            </p>
          </FieldRow>

          <FieldRow n={6} label="Allowed question types">
            <div className="flex flex-wrap gap-2">
              {allowedForMode.map((t) => {
                const on = allowedTypes.includes(t);
                return (
                  <button
                    type="button"
                    key={t}
                    disabled={modeLocksAllowed}
                    onClick={() => setAllowedTypes(toggle(allowedTypes, t))}
                    className={`border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.16em] transition ${
                      on
                        ? "border-[var(--ink)] bg-[var(--ink)] text-[var(--ink-foreground)]"
                        : "border-[var(--paper-rule)] hover:border-[var(--graphite)]"
                    } ${modeLocksAllowed ? "opacity-80" : ""}`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </FieldRow>

          <FieldRow n={7} label="How many of each">
            <div className="flex flex-wrap gap-8">
              <NumberStepper
                label="Objective"
                value={objectiveCount}
                onChange={setObjectiveCount}
              />
              {mode === "Balanced Standard Mode" && (
                <NumberStepper
                  label="Subjective"
                  value={subjectiveCount}
                  onChange={setSubjectiveCount}
                />
              )}
              <div className="self-end font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--graphite)]">
                Total target ·{" "}
                <span className="text-[var(--paper-foreground)]">
                  {objectiveCount + subjectiveCount}
                </span>{" "}
                questions
              </div>
            </div>
          </FieldRow>

          {error ? (
            <div className="border border-[var(--vermillion)] bg-[var(--vermillion)]/5 px-4 py-3 font-mono text-xs text-[var(--vermillion)]">
              {error}
            </div>
          ) : null}

          <div className="flex items-center justify-between border-t border-[var(--paper-rule)] pt-6">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--graphite)]">
              Posts to{" "}
              <span className="text-[var(--paper-foreground)]">
                /api/generate
              </span>
            </p>
            <button
              disabled={submitting}
              className="group inline-flex items-center gap-3 rounded-sm bg-[var(--ink)] px-6 py-3 font-mono text-xs uppercase tracking-[0.22em] text-[var(--ink-foreground)] transition hover:bg-[var(--vermillion)] disabled:opacity-50"
            >
              <span
                aria-hidden
                className="inline-block h-2 w-2 rounded-full bg-[var(--vermillion-soft)] group-hover:bg-[var(--paper)]"
              />
              {submitting ? "Dispatching…" : "Generate candidates"}
              <span aria-hidden className="opacity-60 group-hover:translate-x-1 transition">
                →
              </span>
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

function FieldRow({
  n,
  label,
  children,
}: {
  n: number;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <section className="grid gap-3 md:grid-cols-[7rem_1fr] md:gap-8">
      <div>
        <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-[var(--graphite)]">
          <span className="text-[var(--vermillion)]">
            {String(n).padStart(2, "0")}
          </span>
          <span className="ml-2">{label}</span>
        </div>
      </div>
      <div>{children}</div>
    </section>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none border border-[var(--paper-rule)] bg-[var(--card)] py-2 pl-3 pr-10 font-serif text-lg outline-none focus:border-[var(--vermillion)]"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      <span
        aria-hidden
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 font-mono text-xs text-[var(--graphite)]"
      >
        ▾
      </span>
    </div>
  );
}

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: readonly T[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex flex-wrap border border-[var(--paper-rule)] bg-[var(--card)]">
      {options.map((o) => {
        const on = o === value;
        return (
          <button
            type="button"
            key={o}
            onClick={() => onChange(o)}
            className={`border-r border-[var(--paper-rule)] px-4 py-2 font-mono text-[11px] uppercase tracking-[0.18em] last:border-r-0 transition ${
              on
                ? "bg-[var(--ink)] text-[var(--ink-foreground)]"
                : "hover:bg-[var(--accent)]"
            }`}
          >
            {o}
          </button>
        );
      })}
    </div>
  );
}

function NumberStepper({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  return (
    <div className={disabled ? "opacity-40" : ""}>
      <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--graphite)]">
        {label}
      </div>
      <div className="mt-2 inline-flex items-center border border-[var(--paper-rule)] bg-[var(--card)]">
        <button
          type="button"
          disabled={disabled || value <= 0}
          onClick={() => onChange(Math.max(0, value - 1))}
          className="px-3 py-2 font-mono hover:bg-[var(--accent)] disabled:opacity-30"
        >
          −
        </button>
        <input
          disabled={disabled}
          value={value}
          onChange={(e) => {
            const n = parseInt(e.target.value || "0", 10);
            if (!Number.isNaN(n) && n >= 0 && n <= 50) onChange(n);
          }}
          className="w-12 bg-transparent text-center font-serif text-2xl outline-none"
        />
        <button
          type="button"
          disabled={disabled || value >= 50}
          onClick={() => onChange(Math.min(50, value + 1))}
          className="px-3 py-2 font-mono hover:bg-[var(--accent)] disabled:opacity-30"
        >
          +
        </button>
      </div>
    </div>
  );
}
