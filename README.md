# GapFinder AI

**GapFinder AI is a "doctor for studying."** Students usually revise everything equally and still miss their weak spots, because they can't ask about gaps they don't know they have. GapFinder AI fixes that: a student uploads their syllabus, notes and past papers, and the app tests them, diagnoses their weak topics, prescribes a time-aware revision plan, and keeps updating that plan as they re-test.

The core loop is:

```
Upload → Test → Find weak spots → Plan → Re-test → Plan updates
```

It is built on **RAG (Retrieval-Augmented Generation)** — every quiz question, explanation and answer comes from the student's own uploaded material, never from the model's memory. See [ARCHITECTURE.md](./ARCHITECTURE.md) for how retrieval and generation are split.

## What it does

**Organise your material**

- **Folders.** Uploads are filed into **Syllabus, Notes, Textbook and Past paper** folders (PDF or plain `.txt`).
- **File management.** A three-dot menu on every file offers **View details, Rename and Delete**; a folder's menu offers **View details** and **Delete all files**. Deleting asks for confirmation and says what goes with the file (its quiz questions, or a syllabus's topic map).

**Build a topic map**

- **Topic Build → review → Save.** Pick a syllabus, optionally open its content, and click *Topic Build*. The app extracts the **subject and its topics** and shows them for review (nothing is saved yet). You can rename the subject or remove topics, then click *Save*.
- **Sidebar shortcuts.** Each saved syllabus appears under **Syllabi** in the sidebar (e.g. *Physics Syllabus*, *Chemistry Syllabus*) and opens its own page with **Quiz me** and **Ask** links on every topic.
- Saving links your notes to each topic and maps past-paper questions to topics, which sets each topic's **exam weight**.

**Study from it**

1. **Tests** the student with quiz questions generated only from their own material, each with a chapter/section/page citation.
2. **Diagnoses** which topics are 🔴 Weak, 🟡 Medium or 🟢 Strong, and explains *why* in plain language.
3. **Prescribes** a revision plan that prioritizes the weakest, most exam-important topics first, fitted to the student's available time.
4. **Updates** the plan automatically every time the student re-tests and improves.
5. **Explains** any topic through a tutor that is given the saved syllabus outline as context, so it answers at the right level and says which topic a question belongs to — while still answering **only from the student's notes**.

## Tech stack

These are the choices actually in the code, not options still open.

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 16 (React 19) + Tailwind v4 | Fast UI, easy deployment on Vercel |
| Backend | FastAPI (Python 3.11) | Best PDF and AI tooling in Python |
| Database | PostgreSQL + **pgvector** | One database for relational data and embeddings |
| ORM / migrations | SQLAlchemy 2 (async) + Alembic | Schema is versioned, not hand-written SQL |
| File parsing | PyMuPDF for PDFs, with a `pdfplumber` fallback; plain text for `.txt` | Extracts text with page numbers |
| Embeddings | Gemini `gemini-embedding-001` at 1536-dim (OpenAI `text-embedding-3-small` also supported) | Turns text into vectors for semantic search; sent in batches of 50 with rate-limit retry |
| Vector index | HNSW, `vector_cosine_ops` | Keeps similarity search fast as chunks grow |
| LLM | Any OpenAI-compatible API (default: Google Gemini free tier); Claude also supported | Generates questions, grades answers, writes plans |
| Charts | Recharts | Progress dashboard |
| Auth | JWT (bcrypt password hashes) | Login with demo credentials, no external auth service |

## Project status

**The project is complete and working end to end.** It has been run against a live Supabase Postgres database and Google Gemini's free API: 41 scripted backend checks pass (file management, ownership isolation, topic build/save, quiz, grading, tutor, gap report, plan, dashboard), and every page was clicked through in a real browser.

Known limits:

- **Free-tier quotas.** Gemini's free tier allows about 20 AI requests per day per model, and about 100 embeddings per minute. `LLM_MODEL` lists several models and the app moves to the next when one runs out, but a heavy day can exhaust them, and saving a very large syllabus can take a few minutes.
- **Removing a topic during review** and saving over an already-saved syllabus does not delete the old copy (saving never deletes topics, so quiz history is kept).
- **No automated test suite** is committed; the checks above were run as scripts.
- The demo password `demo123` is for the demo only — change it before any public deployment.

👉 **[RUNNING.md](./RUNNING.md) is the guide to starting the project.** [REMAINING.md](./REMAINING.md) lists optional work.

[EXECUTION.md](./EXECUTION.md) tracks the build phases, [ARCHITECTURE.md](./ARCHITECTURE.md) has the system design, and [GapFinder_AI_Implementation_Plan.md](./GapFinder_AI_Implementation_Plan.md) is the original 12-step plan.

## API at a glance

Interactive docs are at <http://localhost:8000/docs> when the backend is running.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| Files | `POST /documents/upload`, `GET /documents`, `GET/PATCH/DELETE /documents/{id}`, `GET /documents/{id}/content` |
| Topic map | `POST /topics/preview/{document_id}` (Topic Build), `POST /topics/save`, `GET /topics` |
| Syllabi | `GET /syllabi`, `GET /syllabi/{document_id}` |
| Study | `POST /quiz/generate`, `POST /evaluate/answer`, `GET /gap-report`, `POST /gap-report/snapshot`, `POST /plan/generate`, `GET /plan/latest`, `POST /explain`, `GET /dashboard` |

## Repository layout

```
GapFinder AI/
├── frontend/                       # Next.js + Tailwind app
│   └── src/
│       ├── app/
│       │   ├── login/, signup/     # public pages
│       │   └── (app)/              # authenticated: upload, topics, syllabus/[id],
│       │                           #   quiz, gap-report, plan, explain,
│       │                           #   dashboard, how-it-works
│       ├── components/             # ui, KebabMenu (three-dot menu), TopicTree,
│       │                           #   TopicOptions (topic dropdown grouped by syllabus)
│       └── lib/                    # api, types, auth, syllabi (sidebar store),
│                                   #   tree, useApiData
├── backend/                        # FastAPI app
│   ├── app/
│   │   ├── routers/                # auth, upload (files), topics, syllabi, quiz,
│   │   │                           #   evaluate, gap_report, plan, explain, dashboard
│   │   ├── services/               # ingestion, embedding_client, llm_client,
│   │   │                           #   retrieval, topic, topic_map, quiz, evaluation,
│   │   │                           #   gap_report, planning, explain,
│   │   │                           #   retry_policy, schemas
│   │   ├── models/                 # 10 SQLAlchemy models
│   │   ├── schemas/                # Pydantic request/response models
│   │   ├── core/security.py        # bcrypt + JWT
│   │   ├── config.py, database.py, dependencies.py
│   │   └── main.py
│   ├── migrations/versions/        # 0001 initial, 0002, 0003, 0004 (syllabus topic maps)
│   ├── scripts/                    # verify_db, seed_demo, demo_data
│   └── requirements.txt
├── GapFinder_AI_Implementation_Plan.md
├── ARCHITECTURE.md
├── EXECUTION.md
├── REMAINING.md
├── RUNNING.md
└── README.md
```

## Getting started

### Prerequisites

- Node.js 18+ and npm (frontend)
- Python 3.11+ (backend)
- A PostgreSQL database **with the `pgvector` extension** (Supabase, or the `pgvector/pgvector:pg16` Docker image — plain `postgres` will not work)
- One free Google Gemini API key from <https://aistudio.google.com/apikey> (covers both generation and embeddings)

### 1. Configure environment variables

Backend — fill in `backend/.env` (it already exists with the non-secret values set):

```ini
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/postgres
JWT_SECRET=<a long random string>

LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=<free Gemini key>
# Comma list, best first: the app moves to the next model when one hits its daily
# cap or is overloaded. Put stronger models first -- the weakest occasionally
# answers "not covered" wrongly.
LLM_MODEL=gemini-3.5-flash,gemini-3.1-flash-lite,gemini-3.7-flash,gemini-3.8-flash,gemini-3.5-flash-lite

EMBEDDING_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIM=1536
```

Google retires model names over time. If a call fails with a 404, pick a current Flash model from AI Studio and update `LLM_MODEL`.

Three things that will bite you:

- The scheme should be `postgresql+asyncpg://` (a plain `postgresql://` is converted automatically).
- **Remove the `[ ]` brackets** Supabase puts around `[YOUR-PASSWORD]`, and percent-encode any of `@ : / ? #` in the password.
- On Supabase, use the **Direct connection** or **Session pooler** string (port 5432). The **Transaction pooler** (port 6543) runs through pgbouncer, which cannot execute the `CREATE EXTENSION` / `CREATE TYPE` statements the first migration needs.

Frontend (`frontend/.env.local`, copy from `.env.local.example`):

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Set up the backend and database

```bash
cd backend
python -m venv venv
venv\Scripts\activate         # Windows; use source venv/bin/activate elsewhere
pip install -r requirements.txt

alembic upgrade head          # creates the vector extension, 10 tables and their indexes
python -m scripts.verify_db   # confirms the schema landed
python -m scripts.seed_demo   # loads the demo account and sample material
```

The seed makes **zero LLM calls** (it only embeds the sample notes), so it barely touches the free quota.

### 3. Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Check <http://localhost:8000/health> and the interactive API docs at <http://localhost:8000/docs>.

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:3000`, talking to the API at `http://localhost:8000`.

> Don't run `npm run build` while the dev server is running — it overwrites the files the dev server serves, and pages will return 404 until the dev server is restarted.

### 5. Try the demo flow

Log in with the preloaded demo account (`demo@gapfinder.ai` / `demo123`; on the login page click **Use demo account**, then **Log in**) to explore the app without uploading anything — it comes with a Class 10 Science syllabus (already saved, so it shows in the sidebar), notes and a past paper. Or upload your own material and walk through:

```
Upload → Topic Map (Topic Build → Save) → Quiz → Gap Report → Plan → Explain → Retake → Dashboard
```

Follow that order the first time: **the topic map must be saved before quizzes work**, because questions are drawn from the topic↔material links that Save creates. Save makes one LLM call per past-paper question, so give it a minute (longer for a large syllabus). See [RUNNING.md](./RUNNING.md) for the full walkthrough and troubleshooting.

## Build order

1. **Must have** — Upload, topic map, quiz with citations, evaluation, gap report (the core diagnosis loop).
2. **Should have** — Revision plan, "Explain this topic" assistant, progress dashboard.
3. **Nice to have** — Teacher view, spaced repetition, multiple subjects (multiple syllabi per student are supported now).

## Further reading

- [RUNNING.md](./RUNNING.md) — **how to run the project**, plus troubleshooting
- [REMAINING.md](./REMAINING.md) — optional work and known rough edges
- [EXECUTION.md](./EXECUTION.md) — build phases with their current status
- [ARCHITECTURE.md](./ARCHITECTURE.md) — system architecture, database schema, and the retrieval vs. generation breakdown
- [GapFinder_AI_Implementation_Plan.md](./GapFinder_AI_Implementation_Plan.md) — the original step-by-step build plan
