// Types matching docs/api-contract.md exactly. Do not add fields the backend doesn't send/accept.

export type Difficulty = "Easy" | "Balanced" | "Hard";

export interface DifficultyDistribution {
  easy: number;
  medium: number;
  hard: number;
}

export type QuestionType =
  | "MCQ"
  | "FILL_IN_THE_BLANK"
  | "MATCH_THE_COLUMN"
  | "TRUE_FALSE"
  | "ONE_WORD_ANS"
  | "2_MARKS"
  | "3_MARKS"
  | "4_MARKS";

export type ChapterStatus = "pending" | "processing" | "completed" | "failed";

export type OtpPurpose = "signup" | "reset_password";

// ---- Auth ----

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface VerifyOtpSignupResponse {
  message: string;
  access_token: string;
  token_type: string;
}

export interface VerifyOtpResetResponse {
  message: string;
  reset_token: string;
}

export type VerifyOtpResponse = VerifyOtpSignupResponse | VerifyOtpResetResponse;

export interface NotificationSettings {
  fcm_token: string | null;
  notifications_enabled: boolean;
}

// ---- Paper generation ----

export interface PaperGenerateRequest {
  institution_name: string;
  subject: string;
  standard: string;
  difficulty: Difficulty;
  chapters: string[];
  objective_count: number;
  subjective_count: number;
  allowed_types: QuestionType[];
  difficulty_distribution: DifficultyDistribution | null;
}

export interface GenerateResponse {
  thread_id: string;
  status: "generating";
}

export interface ResumeResponse {
  status: "resumed";
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

export type QuestionDifficulty = "Easy" | "Medium" | "Hard";

export interface Question {
  question_text: string;
  question_type: QuestionType;
  chapter: string;
  marks: number;
  // Backend type is a shared 4-value enum (also has "Balanced", used for whole-paper difficulty
  // elsewhere) but this field's own docstring and prompt only ever intend Easy/Medium/Hard —
  // render unknown values gracefully rather than assuming this union is exhaustive at runtime.
  difficulty: QuestionDifficulty;
  options: string[];
  correct_answer: string;
  answer: string;
  evaluation_scheme: EvaluationPoint[];
  diagram_prompt: string | null;
}

export interface UninitializedStatus {
  status: "uninitialized";
}

export interface GeneratingStatus {
  status: "generating";
  progress: Record<string, ChapterProgress>;
}

export interface AwaitingReviewStatus {
  status: "awaiting_review";
  targets: { objective: number; subjective: number };
  questions: Question[];
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
}

export type StatusResponse =
  | UninitializedStatus
  | GeneratingStatus
  | AwaitingReviewStatus
  | CompletedStatus
  | FailedStatus;

export interface SaveToCloudResponse {
  status: "success" | "failed";
}

export interface CancelResponse {
  status: "cancelled";
  message: string;
}

// ---- DB ----

export interface ChapterInfo {
  chapter_name: string;
  subject: string;
  standard: string;
}

export interface PaperHistory {
  id: number;
  thread_id: string;
  created_at: string;
  institution_name: string;
  subject: string;
  standard: string;
  difficulty: string;
  difficulty_distribution: DifficultyDistribution;
  chapters: string[];
  objective_count: number;
  subjective_count: number;
  allowed_types: string[];
  paper_pdf: string;
  answer_pdf: string;
  paper_docx: string;
}
