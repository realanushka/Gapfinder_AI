/**
 * Mirrors the Pydantic schemas in backend/app/schemas/.
 * Keep these in sync with the backend when endpoints change.
 */

export type DocumentType = "syllabus" | "notes" | "textbook" | "past_paper";
export type MasteryStatus = "weak" | "medium" | "strong";

// --- auth ---------------------------------------------------------------
export interface User {
  id: string;
  name: string;
  email: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// --- documents ----------------------------------------------------------
export interface DocumentRecord {
  id: string;
  type: DocumentType;
  filename: string;
  created_at: string;
  /** Searchable chunks the file was split into. */
  chunk_count: number;
  /** Set once a syllabus's topic map has been saved; null otherwise. */
  subject: string | null;
}

/** What "View details" shows for one file. */
export interface DocumentDetails extends DocumentRecord {
  page_count: number;
  topic_count: number;
}

export interface DocumentContent {
  filename: string;
  text: string;
  truncated: boolean;
}

export interface DocumentUploadResponse {
  document: DocumentRecord;
  chunks_created: number;
}

// --- topics -------------------------------------------------------------
export interface TopicRecord {
  id: string;
  name: string;
  parent_id: string | null;
  exam_weight: number;
  /** The syllabus this topic belongs to. */
  document_id: string | null;
}

export interface TopicTreeNode {
  id: string;
  name: string;
  exam_weight: number;
  subtopics: TopicTreeNode[];
}

/** One topic and its subtopic names, before anything is saved. */
export interface TopicDraft {
  name: string;
  subtopics: string[];
}

/** Result of "Topic Build": the extracted structure, not yet persisted. */
export interface TopicPreview {
  document_id: string;
  subject: string;
  topics: TopicDraft[];
}

/** A syllabus whose topic map has been saved; shown as a sidebar shortcut. */
export interface SyllabusSummary {
  document_id: string;
  subject: string;
  filename: string;
  topic_count: number;
}

export interface SyllabusDetail {
  document_id: string;
  subject: string;
  filename: string;
  created_at: string;
  topic_count: number;
  topics: TopicTreeNode[];
}

/** Outcome of saving a topic map, so the UI can report what actually happened. */
export interface TopicBuildResult {
  document_id: string;
  subject: string;
  topics: TopicTreeNode[];
  topics_created: number;
  chunks_linked: number;
  past_questions_mapped: number;
}

// --- quiz ---------------------------------------------------------------
/** options is null for short-answer questions, which are graded by the LLM. */
export interface Question {
  id: string;
  topic_id: string;
  question: string;
  options: Record<string, string> | null;
  source_chunk_id: string;
  citation: string | null;
}

// --- evaluation ---------------------------------------------------------
export interface AnswerResult {
  question_id: string;
  is_correct: boolean | null;
  score: number;
  feedback: string;
  concept_tag: string | null;
}

// --- gap report ---------------------------------------------------------
export interface TopicGapCard {
  topic_id: string;
  topic_name: string;
  score: number;
  status: MasteryStatus;
  reason: string;
  exam_weight: number;
}

// --- plan ---------------------------------------------------------------
export interface PlanTask {
  topic_id: string;
  topic_name: string;
  minutes: number;
  description: string;
  citation: string | null;
}

export interface PlanDay {
  day: number;
  tasks: PlanTask[];
}

/** A topic whose mastery band moved between the last two quiz attempts. */
export interface PlanChange {
  topic_id: string;
  topic_name: string;
  from_status: MasteryStatus;
  to_status: MasteryStatus;
  improved: boolean;
}

export interface PlanResponse {
  id: string;
  created_at: string;
  days: PlanDay[];
  changes: PlanChange[];
}

// --- explain ------------------------------------------------------------
export interface Citation {
  chunk_id: string;
  chapter: string | null;
  section: string | null;
  page: number | null;
}

export interface ExplainResponse {
  answer: string;
  citations: Citation[];
  covered_by_material: boolean;
}

// --- dashboard ----------------------------------------------------------
export interface TopicProgressPoint {
  attempt_no: number;
  score: number;
}

export interface TopicProgress {
  topic_id: string;
  topic_name: string;
  history: TopicProgressPoint[];
}

export interface DashboardResponse {
  readiness_percent: number;
  weak_to_strong_count: number;
  topics: TopicProgress[];
}
