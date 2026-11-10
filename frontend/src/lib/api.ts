/**
 * Typed client for the FastAPI backend.
 *
 * Every call goes through request(), which attaches the JWT and turns non-2xx
 * responses into ApiError carrying FastAPI's `detail` message so pages can show
 * something useful instead of "Failed to fetch".
 */

import type {
  AnswerResult,
  DashboardResponse,
  DocumentContent,
  DocumentDetails,
  DocumentRecord,
  DocumentType,
  DocumentUploadResponse,
  ExplainResponse,
  PlanResponse,
  Question,
  SyllabusDetail,
  SyllabusSummary,
  TokenResponse,
  TopicBuildResult,
  TopicDraft,
  TopicGapCard,
  TopicPreview,
  TopicRecord,
  User,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "gapfinder_token";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; isFormData?: boolean } = {},
): Promise<T> {
  const { method = "GET", body, isFormData = false } = options;

  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined && !isFormData) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    // fetch() only rejects on network-level failures, which in practice means
    // the backend isn't running -- worth saying explicitly.
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is the backend running?`);
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload?.detail)) {
        // FastAPI validation errors arrive as a list of {loc, msg}.
        detail = payload.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ");
      }
    } catch {
      // Non-JSON error body; keep the status-based message.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  if (!text) return null as T;
  return JSON.parse(text) as T;
}

export const api = {
  // --- auth -------------------------------------------------------------
  signup: (name: string, email: string, password: string) =>
    request<User>("/auth/signup", { method: "POST", body: { name, email, password } }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: { email, password } }),

  me: () => request<User>("/auth/me"),

  // --- documents --------------------------------------------------------
  listDocuments: () => request<DocumentRecord[]>("/documents"),

  uploadDocument: (file: File, docType: DocumentType) => {
    const form = new FormData();
    form.append("file", file);
    form.append("doc_type", docType);
    return request<DocumentUploadResponse>("/documents/upload", {
      method: "POST",
      body: form,
      isFormData: true,
    });
  },

  documentDetails: (id: string) => request<DocumentDetails>(`/documents/${id}`),

  /** The extracted text of a file, for previewing before a topic build. */
  documentContent: (id: string) => request<DocumentContent>(`/documents/${id}/content`),

  renameDocument: (id: string, filename: string) =>
    request<DocumentRecord>(`/documents/${id}`, { method: "PATCH", body: { filename } }),

  /** Also removes everything built from the file (chunks, quiz questions, topic map). */
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  // --- topics -----------------------------------------------------------
  listTopics: () => request<TopicRecord[]>("/topics"),

  /** "Topic Build": extracts the structure from a syllabus. Saves nothing. */
  previewTopicMap: (documentId: string) =>
    request<TopicPreview>(`/topics/preview/${documentId}`, { method: "POST" }),

  /** Persists a reviewed map, links notes to topics and weights them by past papers. */
  saveTopicMap: (documentId: string, subject: string, topics: TopicDraft[]) =>
    request<TopicBuildResult>("/topics/save", {
      method: "POST",
      body: { document_id: documentId, subject, topics },
    }),

  // --- syllabi (saved topic maps, shown in the sidebar) -------------------
  listSyllabi: () => request<SyllabusSummary[]>("/syllabi"),

  syllabusDetail: (documentId: string) => request<SyllabusDetail>(`/syllabi/${documentId}`),

  // --- quiz -------------------------------------------------------------
  /**
   * Omit topicId for a retake weighted toward the weakest topics; omit
   * numQuestions to let the backend scale the count by exam weight.
   */
  generateQuiz: (topicId?: string, numQuestions?: number) =>
    request<Question[]>("/quiz/generate", {
      method: "POST",
      body: { topic_id: topicId ?? null, num_questions: numQuestions ?? null },
    }),

  questionsForTopic: (topicId: string) => request<Question[]>(`/quiz/topic/${topicId}`),

  // --- evaluation -------------------------------------------------------
  submitAnswer: (questionId: string, studentAnswer: string) =>
    request<AnswerResult>("/evaluate/answer", {
      method: "POST",
      body: { question_id: questionId, student_answer: studentAnswer },
    }),

  // --- gap report -------------------------------------------------------
  gapReport: () => request<TopicGapCard[]>("/gap-report"),

  /** Records the current scores as a numbered attempt; call once a quiz ends. */
  snapshotGapReport: () => request<TopicGapCard[]>("/gap-report/snapshot", { method: "POST" }),

  // --- plan -------------------------------------------------------------
  generatePlan: (days: number, hoursPerDay: number) =>
    request<PlanResponse>("/plan/generate", {
      method: "POST",
      body: { days, hours_per_day: hoursPerDay },
    }),

  latestPlan: () => request<PlanResponse | null>("/plan/latest"),

  // --- explain ----------------------------------------------------------
  explain: (question: string, topicId?: string) =>
    request<ExplainResponse>("/explain", {
      method: "POST",
      body: { question, topic_id: topicId ?? null },
    }),

  // --- dashboard --------------------------------------------------------
  dashboard: () => request<DashboardResponse>("/dashboard"),
};
