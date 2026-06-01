import type { PaperTypeMode, QuestionType } from "./types";

export const SUBJECTS = [
  "science",
  "mathematics",
  "social science",
  "english",
  "hindi",
] as const;

export const STANDARDS = [
  "6",
  "7",
  "8",
  "9",
  "10",
  "11",
  "12",
] as const;

// Placeholder until /api/metadata is exposed.
export const CHAPTERS_BY_SUBJECT: Record<string, string[]> = {
  Science: [
    "Chemical Reactions and Equations",
    "Acids, Bases and Salts",
    "Metals and Non-metals",
    "Carbon and its Compounds",
    "Life Processes",
    "Light — Reflection and Refraction",
    "The Human Eye and the Colourful World",
    "Electricity",
    "Magnetic Effects of Current",
    "Our Environment",
  ],
  Mathematics: [
    "Real Numbers",
    "Polynomials",
    "Pair of Linear Equations",
    "Quadratic Equations",
    "Arithmetic Progressions",
    "Triangles",
    "Coordinate Geometry",
    "Trigonometry",
    "Circles",
    "Statistics and Probability",
  ],
  "Social Science": [
    "Nationalism in India",
    "Resources and Development",
    "Power Sharing",
    "Money and Credit",
    "Globalisation and the Indian Economy",
  ],
  English: ["A Letter to God", "Nelson Mandela", "Two Stories about Flying"],
  Hindi: ["क्षितिज: पद", "क्षितिज: गद्य", "कृतिका"],
};

// Display labels for the backend enum values.
export const TYPE_LABEL: Record<QuestionType, string> = {
  MCQ: "MCQ",
  FILL_IN_THE_BLANK: "Fill in the Blanks",
  MATCH_THE_COLUMN: "Match the Columns",
  TRUE_FALSE: "True / False",
  ONE_WORD_ANS: "One-Word Answer",
  "2_MARKS": "Short Answer (2 marks)",
  "3_MARKS": "Medium Answer (3 marks)",
  "4_MARKS": "Long Answer (4 marks)",
};

export const OBJECTIVE_TYPES: QuestionType[] = [
  "MCQ",
  "FILL_IN_THE_BLANK",
  "MATCH_THE_COLUMN",
  "TRUE_FALSE",
  "ONE_WORD_ANS",
];

export const SUBJECTIVE_TYPES: QuestionType[] = [
  "2_MARKS",
  "3_MARKS",
  "4_MARKS",
];

export const ALL_QUESTION_TYPES: QuestionType[] = [
  ...OBJECTIVE_TYPES,
  ...SUBJECTIVE_TYPES,
];

export const MODE_ALLOWED: Record<PaperTypeMode, QuestionType[]> = {
  "Balanced Standard Mode": ALL_QUESTION_TYPES,
  "MCQ-Only Mode": ["MCQ"],
  "Objective-Only Mode": OBJECTIVE_TYPES,
};

// Section ordering for the review screen.
export const SECTION_ORDER: QuestionType[] = [
  "MCQ",
  "TRUE_FALSE",
  "FILL_IN_THE_BLANK",
  "ONE_WORD_ANS",
  "MATCH_THE_COLUMN",
  "2_MARKS",
  "3_MARKS",
  "4_MARKS",
];

export function isObjective(t: QuestionType): boolean {
  return OBJECTIVE_TYPES.includes(t);
}
