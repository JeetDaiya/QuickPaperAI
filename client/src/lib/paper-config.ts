import type { DifficultyDistribution, QuestionType } from "@/lib/api/types";

export const DIFFICULTY_PRESETS: Record<string, { label: string; description: string; distribution: DifficultyDistribution }> = {
  balanced: { label: "Balanced", description: "20% E · 50% M · 30% H", distribution: { easy: 20, medium: 50, hard: 30 } },
  foundation: { label: "Foundation", description: "60% E · 30% M · 10% H", distribution: { easy: 60, medium: 30, hard: 10 } },
  challenge: { label: "Challenge", description: "10% E · 30% M · 60% H", distribution: { easy: 10, medium: 30, hard: 60 } },
};

export const OBJECTIVE_TYPES: { value: QuestionType; label: string }[] = [
  { value: "MCQ", label: "Multiple Choice (MCQ)" },
  { value: "FILL_IN_THE_BLANK", label: "Fill in the Blanks" },
  { value: "MATCH_THE_COLUMN", label: "Match the Columns" },
  { value: "TRUE_FALSE", label: "True / False" },
  { value: "ONE_WORD_ANS", label: "One Word Answer" },
];

export const SUBJECTIVE_TYPES: { value: QuestionType; label: string }[] = [
  { value: "2_MARKS", label: "2 Marks (Conceptual)" },
  { value: "3_MARKS", label: "3 Marks (Short Answer)" },
  { value: "4_MARKS", label: "4 Marks (Structured)" },
];

export const ALL_QUESTION_TYPES: QuestionType[] = [...OBJECTIVE_TYPES, ...SUBJECTIVE_TYPES].map((t) => t.value);
export const OBJECTIVE_TYPE_VALUES: QuestionType[] = OBJECTIVE_TYPES.map((t) => t.value);
export const SUBJECTIVE_TYPE_VALUES: QuestionType[] = SUBJECTIVE_TYPES.map((t) => t.value);

export type PaperTypeMode = "standard" | "mcq" | "objective" | "custom";

export const PAPER_TYPE_MODES: Record<PaperTypeMode, { label: string; description: string; allowedTypes: QuestionType[] | null }> = {
  standard: { label: "Balanced Standard Mode", description: "MCQ + Subjective", allowedTypes: ALL_QUESTION_TYPES },
  mcq: { label: "MCQ-Only Mode", description: "Pure Multiple Choice", allowedTypes: ["MCQ"] },
  objective: { label: "Objective-Only Mode", description: "No Long Answers", allowedTypes: OBJECTIVE_TYPE_VALUES },
  // null = user picks freely; not a fixed preset.
  custom: { label: "Custom", description: "Manual toggles", allowedTypes: null },
};
