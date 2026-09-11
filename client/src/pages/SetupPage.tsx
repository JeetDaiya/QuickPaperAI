import { useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import {
  DIFFICULTY_PRESETS,
  OBJECTIVE_TYPES,
  SUBJECTIVE_TYPES,
  ALL_QUESTION_TYPES,
  OBJECTIVE_TYPE_VALUES,
  SUBJECTIVE_TYPE_VALUES,
  PAPER_TYPE_MODES,
  type PaperTypeMode,
} from "@/lib/paper-config";
import { sortNatural } from "@/lib/utils";
import type { ChapterInfo, DifficultyDistribution, PaperGenerateRequest, QuestionType } from "@/lib/api/types";

export interface SetupPageProps {
  chapters: ChapterInfo[];
  schoolName?: string;
  userName?: string;
  userEmail?: string;
  isSubmitting: boolean;
  onSubmit: (payload: PaperGenerateRequest) => void;
  onSignOut: () => void;
}

export function SetupPage({ chapters, schoolName, userName, userEmail, isSubmitting, onSubmit, onSignOut }: SetupPageProps) {
  const [institutionName, setInstitutionName] = useState(schoolName ?? "");
  const [subject, setSubject] = useState("");
  const [standard, setStandard] = useState("");
  const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
  const [distribution, setDistribution] = useState<DifficultyDistribution>(DIFFICULTY_PRESETS.balanced.distribution);
  const [paperTypeMode, setPaperTypeMode] = useState<PaperTypeMode>("standard");
  const [allowedTypes, setAllowedTypes] = useState<QuestionType[]>(ALL_QUESTION_TYPES);
  const [objectiveCount, setObjectiveCount] = useState(20);
  const [subjectiveCount, setSubjectiveCount] = useState(5);

  const isCustomMode = paperTypeMode === "custom";
  const hasObjectiveSelected = useMemo(() => allowedTypes.some((t) => OBJECTIVE_TYPE_VALUES.includes(t)), [allowedTypes]);
  const hasSubjectiveSelected = useMemo(() => allowedTypes.some((t) => SUBJECTIVE_TYPE_VALUES.includes(t)), [allowedTypes]);

  function selectPaperTypeMode(mode: PaperTypeMode) {
    setPaperTypeMode(mode);
    const preset = PAPER_TYPE_MODES[mode].allowedTypes;
    if (preset) setAllowedTypes(preset);
  }

  const subjects = useMemo(() => [...new Set(chapters.map((c) => c.subject))].sort(), [chapters]);
  const standards = useMemo(
    () => [...new Set(chapters.map((c) => c.standard))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })),
    [chapters],
  );
  const availableChapters = useMemo(() => {
    if (!subject || !standard) return [];
    const filtered = chapters.filter((c) => c.subject === subject && c.standard === standard);
    // The backend returns one row per textbook chunk, not one per chapter — dedupe by name.
    const deduped = [...new Map(filtered.map((c) => [c.chapter_name, c])).values()];
    return sortNatural(deduped, (c) => c.chapter_name);
  }, [chapters, subject, standard]);

  const distributionSum = distribution.easy + distribution.medium + distribution.hard;

  function toggleChapter(name: string) {
    setSelectedChapters((prev) => (prev.includes(name) ? prev.filter((c) => c !== name) : [...prev, name]));
  }

  function toggleType(type: QuestionType) {
    setAllowedTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]));
  }

  function difficultyLabel(): "Easy" | "Balanced" | "Hard" {
    if (distribution.hard >= 50) return "Hard";
    if (distribution.easy >= 50) return "Easy";
    return "Balanced";
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (distributionSum !== 100) return;
    onSubmit({
      institution_name: institutionName,
      subject,
      standard,
      difficulty: difficultyLabel(),
      chapters: selectedChapters,
      // The backend rejects a positive count with no allowed types in that category.
      objective_count: hasObjectiveSelected ? objectiveCount : 0,
      subjective_count: hasSubjectiveSelected ? subjectiveCount : 0,
      allowed_types: allowedTypes,
      difficulty_distribution: distribution,
    });
  }

  return (
    <AppShell active="generator" userName={userName} userEmail={userEmail} onSignOut={onSignOut}>
      <div className="flex-grow flex justify-center p-4 md:p-margin-desktop">
        <div className="w-full max-w-container-max bg-surface-container-lowest shadow-sheet rounded-lg border border-outline-variant overflow-hidden">
          <div className="bg-surface-container-low p-6 md:p-8 border-b border-outline-variant">
            <h2 className="font-display-lg text-display-lg text-on-surface tracking-tight leading-tight">Exam Specification</h2>
            <p className="font-body-lg text-body-lg text-on-surface-variant mt-2">Configure requirements for the AI generator</p>
          </div>

          <form className="p-6 md:p-10 space-y-8 max-w-3xl mx-auto" onSubmit={handleSubmit}>
            {/* Section 1 */}
            <div>
              <SectionHeading n={1} title="Administrative Details" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Field label="Institution Name">
                  <input
                    className="input-line font-body-lg text-body-lg text-on-surface font-medium w-full"
                    value={institutionName}
                    onChange={(e) => setInstitutionName(e.target.value)}
                    required
                  />
                </Field>
              </div>
            </div>

            <div className="perforated-divider" />

            {/* Section 2 */}
            <div>
              <SectionHeading n={2} title="Curriculum Mapping" />
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <Field label="Subject">
                  <select
                    className="input-line font-body-lg text-body-lg text-on-surface font-medium w-full"
                    value={subject}
                    onChange={(e) => {
                      setSubject(e.target.value);
                      setSelectedChapters([]);
                    }}
                    required
                  >
                    <option value="" disabled>
                      Select subject…
                    </option>
                    {subjects.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Standard/Grade Level">
                  <select
                    className="input-line font-body-lg text-body-lg text-on-surface font-medium w-full"
                    value={standard}
                    onChange={(e) => {
                      setStandard(e.target.value);
                      setSelectedChapters([]);
                    }}
                    required
                  >
                    <option value="" disabled>
                      Select grade…
                    </option>
                    {standards.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>

              <label className="font-label-md text-label-md text-on-surface-variant mb-2 block">Syllabus Inclusion (Select Chapters)</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {availableChapters.map((c) => (
                  <label
                    key={c.chapter_name}
                    className="flex items-start p-3 border border-outline-variant rounded bg-surface-container-lowest hover:bg-surface-container-low transition-colors cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      className="mt-1 rounded text-primary focus:ring-primary border-outline-variant"
                      checked={selectedChapters.includes(c.chapter_name)}
                      onChange={() => toggleChapter(c.chapter_name)}
                    />
                    <span className="ml-3 block font-label-md text-label-md text-on-surface font-semibold">{c.chapter_name}</span>
                  </label>
                ))}
                {availableChapters.length === 0 && (
                  <p className="font-body-md text-on-surface-variant col-span-2">Select a subject and standard to see chapters.</p>
                )}
              </div>
            </div>

            <div className="perforated-divider" />

            {/* Section 3 */}
            <div>
              <SectionHeading n={3} title="Assessment Parameters" />

              <div className="mb-8 space-y-4">
                <div className="flex items-center justify-between">
                  <label className="font-label-md text-label-md text-on-surface-variant font-semibold">Cognitive Complexity</label>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[12px] font-label-sm font-semibold border ${
                      distributionSum === 100
                        ? "bg-surface-container-high text-on-surface border-outline-variant"
                        : "bg-error-container text-on-error-container border-error/30"
                    }`}
                  >
                    Sum: {distributionSum}% {distributionSum === 100 ? "(Valid)" : "(Must equal 100%)"}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {Object.entries(DIFFICULTY_PRESETS).map(([key, preset]) => {
                    const active =
                      distribution.easy === preset.distribution.easy &&
                      distribution.medium === preset.distribution.medium &&
                      distribution.hard === preset.distribution.hard;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setDistribution(preset.distribution)}
                        className={`flex flex-col items-start p-3 rounded-lg border text-left transition-all ${
                          active ? "border-2 border-primary bg-surface-container-low" : "border-outline-variant bg-surface-container-lowest hover:bg-surface-container-low"
                        }`}
                      >
                        <span className="font-label-md text-label-md font-bold text-on-surface">{preset.label}</span>
                        <span className="font-label-sm text-[11px] text-on-surface-variant mt-1.5">{preset.description}</span>
                      </button>
                    );
                  })}
                </div>
                <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant grid grid-cols-1 md:grid-cols-3 gap-3">
                  {(["easy", "medium", "hard"] as const).map((key) => (
                    <div key={key} className="flex items-center justify-between p-2.5 rounded bg-surface-container-lowest border border-outline-variant">
                      <span className="font-label-sm text-label-sm font-semibold text-on-surface capitalize">{key}</span>
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          min={0}
                          max={100}
                          value={distribution[key]}
                          onChange={(e) => setDistribution((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                          className="input-line w-12 text-right font-bold text-label-md text-on-surface"
                        />
                        <span className="font-label-sm text-on-surface-variant text-label-sm">%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mb-8 space-y-4">
                <label className="font-label-md text-label-md text-on-surface-variant font-semibold block">Paper Type Mode</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {(Object.entries(PAPER_TYPE_MODES) as [PaperTypeMode, (typeof PAPER_TYPE_MODES)[PaperTypeMode]][]).map(
                    ([mode, config]) => {
                      const active = mode === paperTypeMode;
                      return (
                        <button
                          key={mode}
                          type="button"
                          onClick={() => selectPaperTypeMode(mode)}
                          className={`flex flex-col items-start p-3 rounded-lg border text-left transition-all ${
                            active ? "border-2 border-primary bg-surface-container-low" : "border-outline-variant bg-surface-container-lowest hover:bg-surface-container-low"
                          }`}
                        >
                          <span className="font-label-md text-label-md font-bold text-on-surface">{config.label}</span>
                          <span className="font-label-sm text-[11px] text-on-surface-variant mt-1.5">{config.description}</span>
                        </button>
                      );
                    },
                  )}
                </div>
              </div>

              <div className="mb-8 space-y-4">
                <div className="flex items-center justify-between">
                  <label className="font-label-md text-label-md text-on-surface-variant font-semibold block">Allowed Question Types</label>
                  {!isCustomMode ? (
                    <span className="font-label-sm text-[11px] text-on-surface-variant flex items-center gap-1">
                      <span className="material-symbols-outlined text-[14px]">lock</span>
                      Fixed by paper type mode — switch to Custom to edit
                    </span>
                  ) : (
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[12px] font-label-sm font-semibold border ${
                        allowedTypes.length > 0
                          ? "bg-surface-container-high text-on-surface border-outline-variant"
                          : "bg-error-container text-on-error-container border-error/30"
                      }`}
                    >
                      {allowedTypes.length > 0 ? `${allowedTypes.length} Selected` : "Select at least one question type"}
                    </span>
                  )}
                </div>
                <div
                  className={`p-4 rounded-lg bg-surface-container-low border space-y-4 ${
                    isCustomMode && allowedTypes.length === 0 ? "border-error" : "border-outline-variant"
                  }`}
                >
                  <div className="space-y-2">
                    <span className="font-label-sm text-label-sm font-bold text-on-surface uppercase tracking-wider text-[11px]">
                      Objective Formats
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                      {OBJECTIVE_TYPES.filter((t) => paperTypeMode !== "mcq" || t.value === "MCQ").map((t) => (
                        <label
                          key={t.value}
                          className={`flex items-center gap-2.5 p-2.5 rounded bg-surface-container-lowest border border-outline-variant transition-colors ${
                            isCustomMode ? "hover:bg-surface-container-high cursor-pointer" : "opacity-70 cursor-not-allowed"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={allowedTypes.includes(t.value)}
                            disabled={!isCustomMode}
                            onChange={() => toggleType(t.value)}
                            className="rounded text-primary focus:ring-primary border-outline-variant"
                          />
                          <span className="font-label-sm text-label-sm text-on-surface font-medium">{t.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  {paperTypeMode !== "mcq" && paperTypeMode !== "objective" && (
                    <>
                      <div className="perforated-divider my-2" />
                      <div className="space-y-2">
                        <span className="font-label-sm text-label-sm font-bold text-on-surface uppercase tracking-wider text-[11px]">
                          Subjective Formats
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                          {SUBJECTIVE_TYPES.map((t) => (
                            <label
                              key={t.value}
                              className={`flex items-center gap-2.5 p-2.5 rounded bg-surface-container-lowest border border-outline-variant transition-colors ${
                                isCustomMode ? "hover:bg-surface-container-high cursor-pointer" : "opacity-70 cursor-not-allowed"
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={allowedTypes.includes(t.value)}
                                disabled={!isCustomMode}
                                onChange={() => toggleType(t.value)}
                                className="rounded text-primary focus:ring-primary border-outline-variant"
                              />
                              <span className="font-label-sm text-label-sm text-on-surface font-medium">{t.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div>
                <p className="font-label-sm text-[11px] text-on-surface-variant italic mb-3">
                  Counts apply per topic within each chapter — not the whole chapter or the entire paper.
                </p>
                <div className={`grid grid-cols-1 gap-8 ${hasObjectiveSelected && hasSubjectiveSelected ? "md:grid-cols-2" : ""}`}>
                  {hasObjectiveSelected && (
                    <div className="bg-surface-container-low p-4 border border-outline-variant rounded-lg">
                      <label className="font-label-md text-label-md text-on-surface-variant mb-2 block">Objective Questions</label>
                      <input
                        type="number"
                        min={0}
                        value={objectiveCount}
                        onChange={(e) => setObjectiveCount(Number(e.target.value))}
                        className="input-line text-4xl font-display-lg text-primary w-24 text-center"
                      />
                    </div>
                  )}
                  {hasSubjectiveSelected && (
                    <div className="bg-surface-container-low p-4 border border-outline-variant rounded-lg">
                      <label className="font-label-md text-label-md text-on-surface-variant mb-2 block">Subjective Questions</label>
                      <input
                        type="number"
                        min={0}
                        value={subjectiveCount}
                        onChange={(e) => setSubjectiveCount(Number(e.target.value))}
                        className="input-line text-4xl font-display-lg text-secondary w-24 text-center"
                      />
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-8 flex justify-end gap-4">
              <button
                type="submit"
                disabled={
                  isSubmitting ||
                  distributionSum !== 100 ||
                  selectedChapters.length === 0 ||
                  (!hasObjectiveSelected && !hasSubjectiveSelected)
                }
                className="px-8 py-3 bg-primary-container text-on-primary-container rounded font-label-md text-label-md font-bold stamp-shadow hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-60"
              >
                <span className="material-symbols-outlined">bolt</span>
                {isSubmitting ? "Starting…" : "Generate Paper"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppShell>
  );
}

function SectionHeading({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <span className="w-6 h-6 rounded-full bg-secondary text-on-secondary flex items-center justify-center font-label-sm text-label-sm font-bold">
        {n}
      </span>
      <h3 className="font-headline-md text-headline-md-mobile text-on-surface">{title}</h3>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <label className="font-label-md text-label-md text-on-surface-variant mb-1">{label}</label>
      {children}
    </div>
  );
}
