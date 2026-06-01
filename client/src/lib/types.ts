// QuickPaperAI — types matching the FastAPI /api/status response.

export type Difficulty = "Easy" | "Balanced" | "Hard";

export type PaperTypeMode =
  | "Balanced Standard Mode"
  | "MCQ-Only Mode"
  | "Objective-Only Mode";

// Backend question_type enum (string literals as emitted by the API)
export type QuestionType =
  // Objective
  | "MCQ"
  | "FILL_IN_THE_BLANK"
  | "MATCH_THE_COLUMN"
  | "TRUE_FALSE"
  | "ONE_WORD_ANS"
  // Subjective
  | "2_MARKS"
  | "3_MARKS"
  | "4_MARKS";

export type ChapterStatus = "pending" | "processing" | "completed" | "failed";

export type GenerationStatus =
  | "uninitialized"
  | "generating"
  | "awaiting_review"
  | "completed"
  | "failed";

export interface GenerateRequest {
  institution_name: string;
  subject: string;
  standard: string;
  chapters: string[];
  difficulty: Difficulty;
  paper_type_mode: PaperTypeMode;
  allowed_types: QuestionType[];
  objective_count: number;
  subjective_count: number;
}

export interface GenerateResponse {
  thread_id: string;
}

export interface ChapterProgress {
  chapter: string;
  status: ChapterStatus;
  generated_count: number;
}

export interface EvaluationPoint {
  point_text: string;
  allocated_marks: number;
}

export interface QuestionCandidate {
  question_text: string;
  question_type: QuestionType;
  chapter: string;
  marks: number;
  options: string[];
  correct_answer: string;
  answer: string;
  evaluation_scheme: EvaluationPoint[];
  diagram_prompt: string | null;
}

export interface GeneratingStatus {
  status: "generating";
  progress: Record<string, ChapterProgress>;
}

export interface AwaitingReviewStatus {
  status: "awaiting_review";
  targets: { objective: number; subjective: number };
  questions: QuestionCandidate[];
}

export interface CompletedStatus {
  status: "completed";
  files: {
    paper_pdf: string;
    paper_docx: string;
    answer_pdf: string;
  };
}

export interface FailedStatus {
  status: "failed";
  progress?: Record<string, ChapterProgress>;
  error?: string;
}

export interface UninitializedStatus {
  status: "uninitialized";
}

export type StatusResponse =
  | UninitializedStatus
  | GeneratingStatus
  | AwaitingReviewStatus
  | CompletedStatus
  | FailedStatus;

export interface ResumePayload {
  selected_indices: number[];
}
