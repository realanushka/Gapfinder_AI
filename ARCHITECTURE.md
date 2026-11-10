# GapFinder AI — Architecture

This document describes the system as built: the components, data flow, database schema, and the retrieval-vs-generation split that is central to how GapFinder AI works. It started from [GapFinder_AI_Implementation_Plan.md](./GapFinder_AI_Implementation_Plan.md); where the implementation made a different choice from the plan, this document describes what the code actually does.

## 1. High-level overview

GapFinder AI is a RAG (Retrieval-Augmented Generation) application. The guiding rule: **the LLM never answers from its own memory — it only sees chunks retrieved from the student's own uploaded material.** This keeps every quiz question, explanation and gap-report reason traceable to a source page.

```
┌──────────────┐  REST/JSON  ┌───────────────────┐  SQL + vectors  ┌─────────────────────────┐
│  Frontend    │◄───────────►│     Backend       │◄───────────────►│  PostgreSQL + pgvector  │
│  Next.js 16  │  JWT bearer │     FastAPI       │  (async, asyncpg)│  relational + vector    │
│  Tailwind v4 │             │                   │                 │  search in one database │
└──────────────┘             └─────────┬─────────┘                 └─────────────────────────┘
                                       │ OpenAI-compatible API
                                       ▼
                         ┌───────────────────────────┐
                         │   External AI services    │
                         │ • Embeddings (Gemini,     │
                         │   1536-dim)               │
                         │ • LLM (Gemini by default; │
                         │   Claude also supported)  │
                         └───────────────────────────┘
```

The backend is **stateless**: uploaded files are parsed in memory and only their extracted text and embeddings are stored (in the database), so it needs no persistent disk and can run on a free hosting tier (see §8).

## 2. Components

### 2.1 Frontend (Next.js + Tailwind)

Pages map directly to the student's journey. Everything under `(app)/` sits behind a client-side auth gate (JWT in `localStorage`).

| Page | What it does |
|---|---|
| **Upload** | Choose a folder (Syllabus / Notes / Textbook / Past paper) and a file. "Your material" lists each folder; a **three-dot menu** on every file offers *View details, Rename, Delete*, and on every folder *View details, Delete all files*. Deletes confirm first and state what goes with the file. |
| **Topic Map** | Pick a syllabus file, optionally *Open file content*, click **Topic Build** (extracts subject + topics, nothing saved), review/trim, then **Save topic map**. Saved maps are listed per syllabus with exam-frequency badges and *Quiz me* / *Ask* links. |
| **Syllabus page** (`/syllabus/[id]`) | One saved syllabus: its topic tree with study actions. Reached from a **sidebar shortcut** (e.g. "Physics Syllabus"). |
| **Quiz** | Diagnostic quiz with a citation on every question; topic dropdown grouped by syllabus. |
| **Gap Report** | Colour-coded weak / medium / strong topic cards with a one-line reason. |
| **Plan** | Personalised, time-boxed revision schedule with source citations. |
| **Explain** | The tutor: ask a question, optionally focused on one topic. |
| **Dashboard** | Score-over-attempts chart (with a table-view toggle), readiness and weak→strong count. |
| **How it works** | Architecture diagram and the retrieval-vs-generation table (§5). |

Shared building blocks: a typed API client (`lib/api.ts`) that turns FastAPI errors into readable messages; an auth context; a **syllabi store** (`lib/syllabi.tsx`) that feeds the sidebar shortcuts and is refreshed after a save or delete; a reusable `KebabMenu`; `TopicTree` and `TopicOptions` (topic dropdown grouped by syllabus); and a `useApiData` hook that loads data without synchronous state updates in effects.

### 2.2 Backend (FastAPI)

**Routers** (25 endpoints; interactive docs at `/docs`):

| Router | Endpoints |
|---|---|
| `auth` | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| `upload` (files) | `POST /documents/upload`, `GET /documents`, `GET/PATCH/DELETE /documents/{id}`, `GET /documents/{id}/content` |
| `topics` | `POST /topics/preview/{document_id}` (Topic Build), `POST /topics/save`, `POST /topics/build-from-syllabus/{id}` (one-shot), `GET /topics` |
| `syllabi` | `GET /syllabi`, `GET /syllabi/{document_id}` |
| `quiz` | `POST /quiz/generate`, `GET /quiz/topic/{topic_id}` |
| `evaluate` | `POST /evaluate/answer` |
| `gap_report` | `GET /gap-report`, `POST /gap-report/snapshot` |
| `plan` | `POST /plan/generate`, `GET /plan/latest` |
| `explain` | `POST /explain` |
| `dashboard` | `GET /dashboard` |
| — | `GET /health` |

**Services** hold the logic, mirroring the plan's steps:

| Service | Responsibility | Plan step |
|---|---|---|
| `ingestion_service` | PDF (PyMuPDF, with `pdfplumber` fallback) and `.txt` parsing, chapter/section detection, chunking. A new heading always starts a new chunk, so a chunk never straddles two sections and its citation stays correct. | 3 |
| `embedding_client` | Embeds text in **batches of 50** (providers cap a request at 100), preserves order, retries on rate limits, validates vector width. | 3, 4 |
| `retrieval_service` | Vector search: global, scored, and **scoped to one topic's linked chunks**. | 3–9 |
| `topic_service` | Prompts and schemas for topic extraction and past-paper topic confirmation; past-paper splitting. | 4 |
| `topic_map_service` | The save pipeline: upsert topics → link study material → map past papers → recompute exam weights; also builds the **curriculum context** used by the tutor. | 4 |
| `quiz_service` | MCQ / short-answer generation from a chunk, with answer-grounding validation. | 5 |
| `evaluation_service` | Direct MCQ grading; LLM grading of short answers. | 6 |
| `gap_report_service` | Topic scoring and classification (pure code) plus the LLM-written reason. | 7 |
| `planning_service` | Priority and schedule (pure code) plus LLM-written task text. | 8 |
| `explain_service` | Grounded Q&A with citation and refusal behaviour; optional curriculum outline. | 9 |
| `llm_client` | The single place every LLM call goes through (see below). | all |
| `retry_policy` / `schemas` | Shared retry policy; JSON Schemas for structured outputs. | all |

**The LLM client** supports two backends chosen by `LLM_PROVIDER`: `openai_compatible` (Gemini, Groq, OpenRouter, …; the default here) and `anthropic`. Notable behaviour:

- **Model fallback chain.** `LLM_MODEL` may list several models, best first. On a quota (429), overload (503) or retired-model (404) response the client moves to the next and remembers it. This matters on free tiers, which cap each model separately.
- **Structured output.** Every JSON call passes a JSON Schema. Claude enforces it natively; OpenAI-compatible providers get it in the prompt and the reply is verified in code (required keys, types, enums). A bad reply is resampled by the retry layer.
- **Failure modes are typed** (`LLMNotConfigured`, `LLMRefused`, `LLMOutputTruncated`, …). The app converts provider errors into a readable **HTTP 503** rather than a bare 500.

**Cross-cutting rules**

- **Ownership.** Every file, topic and syllabus lookup is scoped to the signed-in user; someone else's id behaves like a missing one (404).
- **Validation before writing.** An upload is parsed and chunked *before* any database row is created, so a corrupt, empty or image-only file leaves nothing behind. Topic maps are capped (60 topics, 30 subtopics each) so a bad extraction cannot flood the embedding API.
- **Passwords** are hashed with bcrypt (inputs truncated to its 72-byte limit consistently on hash and verify); sessions are JWTs.

### 2.3 Database (PostgreSQL + pgvector)

A single database holds both relational data and vector embeddings, avoiding a separate vector store. `chunks.embedding` is `vector(1536)` with an **HNSW index** (`vector_cosine_ops`). The schema is versioned with Alembic: `0001` initial schema, `0002` past-question → document link, `0003` attempt score and concept tag, `0004` syllabus topic maps (`documents.subject`, `topics.document_id`).

### 2.4 External AI services

- **Embeddings** — `gemini-embedding-001` requested at 1536 dimensions (OpenAI `text-embedding-3-small` is also supported). Cosine similarity is scale-invariant, so the provider's lack of normalisation at this width does not matter.
- **LLM** — used only for generation tasks: topic extraction, question writing, short-answer grading narrative, diagnosis text, plan task descriptions and the Explain tutor.

## 3. Database schema

10 tables:

| Table | Key columns | Purpose |
|---|---|---|
| `users` | id, name, email (unique), password_hash | Accounts, including the preloaded demo account |
| `documents` | id, user_id, type (syllabus / notes / textbook / past_paper), filename, **subject**, created_at | Uploaded files. `subject` is set when a syllabus's topic map is saved — non-null means "saved", and it is the sidebar label |
| `chunks` | id, document_id, text, chapter, section, page, embedding `vector(1536)` | Chunked, embedded text with citation metadata |
| `topics` | id, user_id, name, parent_id, exam_weight, **document_id** | Topic tree; `document_id` is the syllabus it came from, so several syllabi coexist |
| `chunk_topics` | chunk_id, topic_id | Link between material chunks and topics |
| `past_questions` | id, text, topic_id, year, document_id | Questions extracted from past papers |
| `questions` | id, topic_id, question, options (JSONB), correct_answer, source_chunk_id, explanation | Generated quiz questions, each tied to its source chunk |
| `attempts` | id, user_id, question_id, student_answer, is_correct, score, concept_tag, feedback, timestamp | Student answers and grading results |
| `topic_scores` | user_id, topic_id, attempt_no, score, status (weak/medium/strong), reason | Per-topic mastery over time, feeding the gap report and dashboard |
| `plans` | user_id, plan_json (JSONB), created_at | Generated revision plans |

Relationships: `documents → chunks → chunk_topics → topics`; `documents (syllabus) → topics`; `topics → past_questions` (exam weight) and `topics → questions` (quiz); `questions → attempts → topic_scores → plans`.

**Deletion cascades** (these are why the UI warns before deleting):

| Deleting… | Also removes |
|---|---|
| a notes / textbook file | its chunks, the links to topics, the quiz questions drawn from those chunks, and the attempts on them |
| a syllabus | its topics, and with them their questions, attempts and scores |
| a past paper | its extracted questions; exam weights are recomputed |
| a user | everything above |

## 4. End-to-end data flow

1. **Ingestion** (Step 3): Upload → parse in memory (PDF or text) → detect chapter/section headings → chunk (~400 words, small overlap, new chunk at every heading) → embed in batches → store in `chunks` with citation metadata. The file is stored in the folder matching the chosen type.
2. **Topic Build** (Step 4a): Syllabus text → LLM → a **subject** and a topic tree, returned for review. **Nothing is written.**
3. **Save topic map** (Step 4b): The reviewed tree is upserted into `topics` (existing topics are reused, so quiz history survives a re-save; a topic from another syllabus is never touched) and `documents.subject` is set. Each topic is then embedded **together with its subtopic names** (a bare title like "Nutrition" is too short to embed well) and linked to its closest study-material chunks, keeping only chunks within a similarity margin of that topic's best match — otherwise a small set of notes attaches to every topic. Past-paper questions are split, matched to topics by embedding similarity, confirmed by the LLM, and counted into each topic's `exam_weight`. Past papers are re-mapped against *all* the student's topics so saving a second syllabus does not wipe the first one's mappings.
4. **Quiz generation** (Step 5): For a topic, take its linked chunks (unused ones first, so retakes ask new questions) → LLM writes an MCQ or short answer from that text, given the subject and topic name as orientation → validate that the answer is grounded in the chunk (content-word overlap) → discard failures → store in `questions` with `source_chunk_id`.
5. **Evaluation** (Step 6): MCQs graded by direct comparison (no AI). Short answers graded by the LLM given the question, answer and source chunk → verdict, score (clamped to 0–1 in code), reason, concept tag.
6. **Gap report** (Step 7): per topic, score the latest attempt on each question → classify 🔴 weak / 🟡 medium / 🟢 strong → LLM writes a one-line reason from the wrong answers and concept tags. `GET` is a pure read; `POST /snapshot` records a numbered attempt in `topic_scores`.
7. **Revision plan** (Step 8): time available + `priority = (1 − mastery) × exam_weight` computed in code → schedule built in code → LLM writes the task descriptions, each linked to a real chapter/section/page.
8. **Explain tutor** (Step 9): the question is embedded; if a topic is chosen, retrieval is **restricted to that topic's linked chunks** (falling back to all material if none are linked). The system prompt also carries the **saved syllabus outline** and "the student is currently studying X (part of Y)". The outline is explicitly orientation only — every fact must come from the retrieved chunks. The tutor cites sources, says which topic the question belongs to, or refuses if the material does not cover it.
9. **Re-test loop & dashboard** (Step 10): retakes favour weak topics and unused chunks; each snapshot adds an attempt number; the dashboard charts score-over-attempts, readiness and weak→strong transitions.

## 5. Retrieval vs. generation — the core design constraint

The problem statement requires this separation to be explicit, and it is the architectural backbone of the system:

| Step | Retrieval (looks up the student's material) | Generation (LLM writes) |
|---|---|---|
| Topic Build | None — reads the syllabus text itself | Extracts subject and topics |
| Save topic map | Links chunks and past questions to topics by vector similarity | LLM confirms which topic a past question belongs to |
| Quiz | Fetches the chunks linked to a topic | Writes questions from those chunks only |
| Evaluation | Fetches the source chunk | Explains right or wrong |
| Gap report | None — scores computed in code | Writes the reason text |
| Plan | None — priority computed in code | Writes the task descriptions |
| Explain | Fetches the top chunks (topic-scoped if a topic is chosen) | Answers from those chunks only; the syllabus outline only frames the answer |

**How separation is enforced:**

- The LLM is never given anything except the retrieved chunks relevant to the current task. The syllabus outline passed to the quiz and tutor is labelled as orientation, never as a source of facts.
- Every generated question carries a `source_chunk_id` for traceability.
- Generated questions are validated against their source chunk before being shown; failures are discarded.
- All scores, classifications and scheduling priorities are computed deterministically in backend code — never by the LLM — so they remain explainable and reproducible.

## 6. Reliability on free tiers

The system is designed to degrade gracefully on free AI and hosting plans:

| Constraint | Behaviour |
|---|---|
| Per-model daily LLM quota (about 20 requests) | Fallback chain across several models; if all are exhausted the API returns a clear 503 and non-AI pages keep working. |
| Embedding batch limit (100) and per-minute limit | Batches of 50; on a 429 the batch waits and retries, so a big syllabus or textbook completes (slowly) instead of failing. |
| Transient provider errors | SDK-level retries for transport failures, plus a retry layer for unusable-but-successful responses (malformed JSON, wrong vector width). Permanent failures (bad key, refusal, truncation) are not retried. |
| Weak free models answering "not covered" wrongly | Stronger models are listed first in `LLM_MODEL`. |

## 7. Security model

- **Authentication:** bcrypt password hashes, JWT bearer tokens.
- **Authorisation:** all data access is filtered by the signed-in user; cross-user access returns 404.
- **Secrets:** database URL, API keys and the JWT secret are kept in the single root `.env`, which is git-ignored. Only the backend reads them. The frontend loads the same file, but Next.js exposes only `NEXT_PUBLIC_*` variables to the browser, and the only one is `NEXT_PUBLIC_API_URL`, which is not secret. Secrets never reach the browser or the repository. `.env.example` is the committed template with placeholder values.
- **Known gap:** there is no rate limiting on signup or AI endpoints, and the demo account's password is public by design. Both matter once the app is exposed publicly (see [DEPLOYING.md](./DEPLOYING.md) §8).

## 8. Configuration and deployment

### Configuration: one root `.env`

```
GapFinder AI/.env ──► backend/app/config.py    (pydantic-settings, absolute path to the root file)
                  └─► frontend/next.config.ts  (@next/env loadEnvConfig on the parent folder)
```

- **Backend:** `Settings` in `backend/app/config.py` sets `env_file` to `Path(__file__).resolve().parents[2] / ".env"`. The file is therefore found no matter which folder `uvicorn`, `alembic` (`migrations/env.py`) or `scripts/seed_demo` is started from.
- **Frontend:** Next.js reads `.env` files only from its own folder, so `next.config.ts` calls `loadEnvConfig` on the repository root before the app compiles. `NEXT_PUBLIC_API_URL` is then inlined into the browser bundle as usual.
- **Precedence:** variables already set in the process environment win over the file. On Render and Vercel the values come from each dashboard and no `.env` file exists. The same code works locally and in production without changes.
- **Full variable list:** `.env.example` and the README's *Configure environment variables* section.

### Deployment

```
Browser ──► Vercel (Next.js) ──► Render (FastAPI) ──► Supabase (Postgres + pgvector)
                                        └──────────► Gemini API (LLM + embeddings)
```

- **Frontend**: Vercel (free Hobby plan). `NEXT_PUBLIC_API_URL` is baked in at build time.
- **Backend**: Render free web service. Stateless, so no disk is needed. `CORS_ORIGINS` must list the frontend origin.
- **Database**: Supabase free tier (PostgreSQL + pgvector), reached through the **Session pooler on port 5432** — the Transaction pooler (6543) breaks asyncpg.

Consequences of the free tiers: the backend **sleeps after ~15 minutes idle** (first request ~30–60 s) and Supabase **pauses after ~7 days of inactivity**. Step-by-step instructions, environment variables and troubleshooting are in [DEPLOYING.md](./DEPLOYING.md).

## 9. Build order / architectural priority

1. **Core diagnosis loop (must have)** — ingestion → topic map → quiz with citations → evaluation → gap report. *Done.*
2. **Adaptive loop (should have)** — revision plan → explain assistant → dashboard. *Done.*
3. **Beyond the plan (done)** — folders and file management, review-then-save topic maps, multiple syllabi with sidebar shortcuts, curriculum-aware quiz and tutor.
4. **Extensions (not built)** — teacher view, spaced repetition.
