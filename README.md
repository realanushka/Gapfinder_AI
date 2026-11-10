# GapFinder AI

**GapFinder AI is a "doctor for studying."** Students usually revise everything equally and still miss their weak spots, because they can't ask about gaps they don't know they have. GapFinder AI fixes that: a student uploads their syllabus, notes and past papers, and the app tests them, diagnoses their weak topics, prescribes a time-aware revision plan, and keeps updating that plan as they re-test.

The core loop is:

```
Upload → Test → Find weak spots → Plan → Re-test → Plan updates
```

It is built on **RAG (Retrieval-Augmented Generation)** — every quiz question, explanation and answer comes from the student's own uploaded material, never from the model's memory. See [ARCHITECTURE.md](./ARCHITECTURE.md) for how retrieval and generation are split.

## Try the demo

A demo account comes preloaded, so anyone can try the app without uploading anything.

| | |
|---|---|
| **Live site** | `<add your Vercel URL here after deploying>` |
| **Email** | `demo@gapfinder.ai` |
| **Password** | `demo123` |

On the login page click **Use demo account** (it fills in the fields), then **Log in**.

> On the live site, the first request after a quiet spell can take **30–60 seconds**, because the free backend server is waking up. Wait and try again.

### What's already in the demo account

| Item | Details |
|---|---|
| Syllabus | `class10_science_syllabus.txt`, *Class 10 Science, Unit 2: Life Processes*. Its topic map is **already saved**, so it appears under **Syllabi** in the sidebar |
| Topics | 3 topics with 2 subtopics each: **Nutrition** (autotrophic/photosynthesis, heterotrophic), **Respiration** (aerobic, anaerobic), **Transportation** (in human beings, in plants) |
| Notes | `life_processes_notes.txt`, 6 sections linked to the topics, with chapter and page citations |
| Past paper | `science_board_2023.txt`, 6 questions (Q1–Q3 Nutrition, Q4–Q5 Respiration, Q6 Transportation). These set each topic's exam weight: Nutrition 3, Respiration 2, Transportation 1 |
| Quiz questions | 7 ready-made questions (3 Nutrition, 2 Respiration, 2 Transportation) |
| Score history | 3 past attempts per topic showing improvement, so the **Dashboard** has charts from the first login |

Score history (fraction answered correctly):

| Topic | Attempt 1 | Attempt 2 | Attempt 3 |
|---|---|---|---|
| Nutrition | 33% 🔴 | 67% 🟡 | 100% 🟢 |
| Respiration | 50% 🔴 | 50% 🔴 | 100% 🟢 |
| Transportation | 50% 🔴 | 100% 🟢 | 100% 🟢 |

### Suggested 5-minute walkthrough

1. **Dashboard:** see the improvement over three attempts.
2. **Sidebar → Class 10 Science:** open the syllabus page, which has **Quiz me** and **Ask** links on every topic.
3. **Quiz:** pick *Nutrition* and generate questions. Each one cites the chapter and page of the notes it came from. Answer them, including one wrong answer on purpose.
4. **Gap Report:** see which topics are 🔴 Weak, 🟡 Medium or 🟢 Strong, with a plain-language reason for each.
5. **Plan:** click generate. You get a revision plan that puts the weakest, most exam-important topics first. The demo account doesn't include a saved plan, so it is generated on this click.
6. **Explain:** ask, for example, *"Why does the light reaction need water?"* The tutor answers only from the uploaded notes.
7. **Upload your own (optional):** add a PDF or `.txt` to **Notes**, add a syllabus, then run **Topic Map → Topic Build → Save topic map**. Saving takes about 30–60 seconds.

### Good to know

- **Shared account.** Everyone who uses the demo login shares the same data. To restore it to the original state, run `python -m scripts.seed_demo` in `backend/`. The script is safe to re-run: it wipes the demo account's data and loads it again.
- **AI limits.** Quiz generation, grading, Gap Report reasons, Plan and Explain use Google Gemini's free tier, about 20 requests per day per model. If you see a *quota* message, try again later. Browsing the uploaded files, topics and dashboard keeps working.
- **Demo only.** `demo123` is a public password. Don't store real data in this account.

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

👉 **[RUNNING.md](./RUNNING.md) is the guide to starting the project locally**, and **[DEPLOYING.md](./DEPLOYING.md) is the guide to putting it live for free** (Vercel + Render + Supabase). [REMAINING.md](./REMAINING.md) lists optional work.

[EXECUTION.md](./EXECUTION.md) tracks the build phases, [ARCHITECTURE.md](./ARCHITECTURE.md) has the system design, and [GapFinder_AI_Implementation_Plan.md](./GapFinder_AI_Implementation_Plan.md) is the original 12-step plan.

## API at a glance

Interactive docs are at <http://localhost:8000/docs> when the backend is running.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| Files | `POST /documents/upload`, `GET /documents`, `GET/PATCH/DELETE /documents/{id}`, `GET /documents/{id}/content` |
| Topic map | `POST /topics/preview/{document_id}` (Topic Build), `POST /topics/save`, `POST /topics/build-from-syllabus/{document_id}` (one-shot build + save), `GET /topics` |
| Syllabi | `GET /syllabi`, `GET /syllabi/{document_id}` |
| Study | `POST /quiz/generate`, `GET /quiz/topic/{topic_id}`, `POST /evaluate/answer`, `GET /gap-report`, `POST /gap-report/snapshot`, `POST /plan/generate`, `GET /plan/latest`, `POST /explain`, `GET /dashboard` |
| Health | `GET /health` |

25 endpoints in total. See [ARCHITECTURE.md](./ARCHITECTURE.md) for what each one does.

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
├── GapFinder_AI_Implementation_Plan.md   # original 12-step plan
├── ARCHITECTURE.md                       # system design (as built)
├── RUNNING.md                            # run locally + troubleshooting
├── DEPLOYING.md                          # free hosting: Vercel + Render + Supabase
├── EXECUTION.md                          # build phases and status
├── REMAINING.md                          # optional work
└── README.md
```

## Getting started

### Prerequisites

- Node.js 18+ and npm (frontend)
- Python 3.11+ (backend)
- A PostgreSQL database **with the `pgvector` extension** (Supabase, or the `pgvector/pgvector:pg16` Docker image — plain `postgres` will not work)
- One free Google Gemini API key from <https://aistudio.google.com/apikey> (covers both generation and embeddings)

### 1. Configure environment variables

The whole project uses **one `.env` file in the root folder**, shared by the backend and the frontend. Copy the template and fill it in:

```powershell
copy .env.example .env      # Windows (cp .env.example .env elsewhere)
```

The backend reads it through `backend/app/config.py`, and the frontend through `frontend/next.config.ts`. Variables that are already set in the environment, such as those on Render or Vercel, take precedence over the file. The key settings:

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

Frontend (same root `.env`):

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

Log in with the preloaded demo account (`demo@gapfinder.ai` / `demo123`). See **[Try the demo](#try-the-demo)** above for what it contains and a suggested walkthrough. Or upload your own material and walk through:

```
Upload → Topic Map (Topic Build → Save) → Quiz → Gap Report → Plan → Explain → Retake → Dashboard
```

Follow that order the first time: **the topic map must be saved before quizzes work**, because questions are drawn from the topic↔material links that Save creates. Save makes one LLM call per past-paper question, so give it a minute (longer for a large syllabus). See [RUNNING.md](./RUNNING.md) for the full walkthrough and troubleshooting.

## Deploying for free

The whole app can run on free plans:

```
Browser ──► Vercel (Next.js) ──► Render (FastAPI) ──► Supabase (Postgres + pgvector)
                                        └──────────► Gemini API (LLM + embeddings)
```

| Part | Service | Notes |
|---|---|---|
| Frontend | **Vercel** (Hobby) | Free plan is for non-commercial use. `NEXT_PUBLIC_API_URL` is set at build time. |
| Backend | **Render** (free web service) | Stateless, so no disk is needed. Sleeps after ~15 min idle; the first request then takes ~30–60 s. |
| Database | **Supabase** (free) | Includes pgvector. Pauses after ~7 days of inactivity; restore it from the dashboard. |

Things to know before sharing a public link:

- The Gemini free tier is shared by every visitor (about 20 AI requests per day per model), so the quiz and tutor can run out on a busy day. The non-AI pages keep working.
- Set a new `JWT_SECRET`, set `CORS_ORIGINS` to your frontend URL, and decide what to do with the public demo login (`demo123`).
- There is no rate limiting on signup or the AI endpoints yet.

The full step-by-step guide, environment variables and troubleshooting are in **[DEPLOYING.md](./DEPLOYING.md)**.

## Build order

1. **Must have** — Upload, topic map, quiz with citations, evaluation, gap report (the core diagnosis loop).
2. **Should have** — Revision plan, "Explain this topic" assistant, progress dashboard.
3. **Nice to have** — Teacher view, spaced repetition, multiple subjects (multiple syllabi per student are supported now).

## Further reading

- [RUNNING.md](./RUNNING.md) — **how to run the project**, plus troubleshooting
- [DEPLOYING.md](./DEPLOYING.md) — **how to put it live for free** (Vercel + Render + Supabase)
- [REMAINING.md](./REMAINING.md) — optional work and known rough edges
- [EXECUTION.md](./EXECUTION.md) — build phases with their current status
- [ARCHITECTURE.md](./ARCHITECTURE.md) — system architecture, database schema, and the retrieval vs. generation breakdown
- [GapFinder_AI_Implementation_Plan.md](./GapFinder_AI_Implementation_Plan.md) — the original step-by-step build plan
