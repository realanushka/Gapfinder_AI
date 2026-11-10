# GapFinder AI — Architectural Structure

This document describes the system architecture derived from [GapFinder_AI_Implementation_Plan.md](./GapFinder_AI_Implementation_Plan.md): the components, data flow, database schema, and the retrieval-vs-generation split that is central to how GapFinder AI works.

## 1. High-level overview

GapFinder AI is a RAG (Retrieval-Augmented Generation) application. The guiding rule: **the LLM never answers from its own memory — it only sees chunks retrieved from the student's own uploaded material.** This keeps every quiz question, explanation and gap-report reason traceable to a source page.

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────────────┐
│  Frontend   │◄────►│     Backend      │◄────►│  PostgreSQL + pgvector  │
│ Next.js +   │ REST │    FastAPI       │ SQL/ │  (relational + vector   │
│ Tailwind    │      │                  │ Vec  │   search in one DB)     │
└─────────────┘      └─────┬────────────┘      └─────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │ External AI services  │
                │ - Embedding model      │
                │ - LLM (Claude/GPT/     │
                │   Gemini)              │
                └───────────────────────┘
```

## 2. Components

### 2.1 Frontend (Next.js + Tailwind)

Pages map directly to the student's journey:

- **Upload** — upload syllabus, notes, textbook, past papers.
- **Topic Map** — syllabus-derived topic tree with exam-frequency badges.
- **Quiz** — diagnostic quiz with citations per question.
- **Gap Report** — colour-coded weak/medium/strong topic cards.
- **Plan** — personalized, time-boxed revision schedule.
- **Explain** — "Explain this topic" RAG assistant.
- **Dashboard** — progress charts across quiz attempts.
- **How it works** — architecture diagram and retrieval-vs-generation table (see §5), to satisfy the problem statement's requirement to make this explicit.

### 2.2 Backend (FastAPI)

Organized by responsibility, mirroring the implementation plan's steps:

| Service | Responsibility | Plan step |
|---|---|---|
| `ingestion` | PDF/text parsing, structure detection (chapters/sections), chunking | Step 3 |
| `embeddings` | Generate and store vector embeddings for chunks and topics | Step 3, 4 |
| `topics` | Syllabus → topic tree extraction; topic-to-material and topic-to-past-question linking; exam weighting | Step 4 |
| `quiz` | Question generation per topic from retrieved chunks, with validation against source | Step 5 |
| `evaluation` | Grade MCQ/short answers, generate explanations and concept tags | Step 6 |
| `gap_report` | Score topics, classify weak/medium/strong, generate diagnosis text | Step 7 |
| `planning` | Compute priority scores and schedule (pure code), generate task descriptions (LLM) | Step 8 |
| `explain` | Retrieval-grounded Q&A assistant with citation and refusal behavior | Step 9 |
| `dashboard` | Aggregate attempt history for charts and readiness metrics | Step 10 |
| `auth` | Signup/login, demo account, JWT/session handling | Step 2 |

### 2.3 Database (PostgreSQL + pgvector)

A single database holds both relational data and vector embeddings, avoiding a separate vector store.

### 2.4 External AI services

- **Embedding model** (e.g. `text-embedding-3-small`, or `bge-small` for a free option) — converts text into vectors for semantic search.
- **LLM** (Claude, GPT, or Gemini) — used only for generation tasks: topic extraction, question writing, answer grading narrative, diagnosis text, plan task descriptions, and the Explain assistant.

## 3. Database schema

| Table | Key columns | Purpose |
|---|---|---|
| `users` | id, name, email, password_hash | Accounts, including the preloaded demo account |
| `documents` | id, user_id, type (syllabus / notes / textbook / past_paper), filename | Uploaded source files |
| `chunks` | id, document_id, text, chapter, section, page, embedding (vector) | Chunked, embedded source text with citation metadata |
| `topics` | id, user_id, name, parent_id, exam_weight | Topic tree extracted from the syllabus |
| `chunk_topics` | chunk_id, topic_id | Many-to-many link between material chunks and topics |
| `past_questions` | id, text, topic_id, year | Individual questions extracted from past papers |
| `quizzes` / `questions` | id, topic_id, question, options, correct_answer, source_chunk_id | Generated diagnostic questions, each tied to a source chunk |
| `attempts` / `answers` | id, user_id, question_id, student_answer, is_correct, feedback, timestamp | Student responses and grading results |
| `topic_scores` | user_id, topic_id, attempt_no, score, status (weak/medium/strong), reason | Per-topic mastery over time, feeding the gap report and dashboard |
| `plans` | user_id, plan_json, created_at | Generated revision plans, regenerated after each new attempt |

Relationships, in short: `documents → chunks → chunk_topics → topics`; `topics → past_questions` (exam weight) and `topics → questions` (quiz); `questions → attempts/answers → topic_scores → plans`.

## 4. End-to-end data flow

1. **Ingestion** (Step 3): Upload → extract text per page → detect chapter/section structure → chunk (~300–500 words, slight overlap) → embed → store in `chunks` with citation metadata (document, chapter, section, page).
2. **Topic mapping** (Step 4): Syllabus text → LLM → strict JSON topic tree → `topics`. Topic name embeddings → vector search over `chunks` → `chunk_topics`. Past-paper questions → split → matched to topics by embedding similarity + LLM confirmation → `past_questions`. Exam weight = count of past questions per topic.
3. **Quiz generation** (Step 5): For each topic, retrieve its linked chunks → LLM generates an MCQ strictly from that text → validate the answer appears in the source chunk → discard if validation fails → store in `questions` with `source_chunk_id`.
4. **Evaluation** (Step 6): MCQs graded by direct comparison (no AI). Short answers graded by LLM given the question, student answer, and source chunk → JSON verdict (correct/partial/wrong) + score + reason + concept tag.
5. **Gap report** (Step 7): `score = correct / total` per topic → classify 🔴 <50%, 🟡 50–75%, 🟢 >75% → LLM writes a one-line diagnosis from the wrong answers and concept tags → UI renders sorted, colour-coded cards.
6. **Revision plan** (Step 8): Student enters available time → `priority = (1 - mastery) × exam_weight` computed in code → schedule built in code (more time to weaker topics) → LLM writes human-readable task descriptions linked to source sections → plan regenerates after every new attempt.
7. **Explain assistant** (Step 9): Student question/topic click → retrieve top 4–6 chunks from their material → LLM answers strictly from that context with citations, or explicitly refuses if the material doesn't cover it.
8. **Re-test loop & dashboard** (Step 10): "Retake quiz" generates new questions weighted toward weak topics → each attempt stored with an attempt number in `topic_scores` → dashboard charts score-over-attempts, overall readiness, and weak→strong transitions.

## 5. Retrieval vs. generation — the core design constraint

The problem statement requires this separation to be explicit, and it is the architectural backbone of the system:

| Step | Retrieval (looks up the student's material) | Generation (LLM writes) |
|---|---|---|
| Topic map | Matches chunks and past questions to topics | Extracts topics from the syllabus |
| Quiz | Fetches the chunks for a topic | Writes questions from those chunks only |
| Evaluation | Fetches the source chunk | Explains right or wrong |
| Gap report | None — scores computed in code | Writes the reason text |
| Plan | None — priority computed in code | Writes the task descriptions |
| Explain | Fetches the top chunks | Answers from those chunks only |

**How separation is enforced:**

- The LLM is never given anything except the retrieved chunks relevant to the current task.
- Every generated question and answer carries a `source_chunk_id` for traceability.
- Generated questions are validated against their source chunk before being shown; failures are discarded.
- All scores, classifications, and scheduling priorities are computed deterministically in backend code — never by the LLM — so they remain explainable and reproducible.

## 6. Deployment

- **Frontend**: Vercel (Next.js).
- **Backend**: Render or Railway (FastAPI).
- **Database**: Supabase (PostgreSQL + pgvector), reachable from both.

## 7. Build order / architectural priority

1. **Core diagnosis loop (must have)**: ingestion → topic map → quiz with citations → evaluation → gap report.
2. **Adaptive loop (should have)**: revision plan → explain assistant → dashboard.
3. **Extensions (nice to have)**: teacher view, spaced repetition, multi-subject support.
