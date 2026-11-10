# RUNNING.md — how to run GapFinder AI

Everything here was run and verified on this machine (Windows, Python 3.11,
Node, Supabase Postgres, Google Gemini free tier).

## One-time setup (already done on this machine)

1. `backend/.env` is filled in: `DATABASE_URL`, `JWT_SECRET`, `LLM_API_KEY`
   (free Gemini key from <https://aistudio.google.com/apikey>).
2. Database tables created and demo data loaded:

   ```powershell
   cd "D:\GapFinder AI\backend"
   .\venv\Scripts\Activate.ps1
   alembic upgrade head
   python -m scripts.seed_demo
   ```

   Re-running the seed is safe. Only run `alembic upgrade head` again if a new
   migration is added.

## Every time: start the two servers

Open **two** terminals and leave both running.

**Terminal 1 — backend (API on port 8000)**

```powershell
cd "D:\GapFinder AI\backend"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Check: <http://localhost:8000/health> → `{"status":"ok"}`;
API docs at <http://localhost:8000/docs>.

**Terminal 2 — frontend (website on port 3000)**

```powershell
cd "D:\GapFinder AI\frontend"
npm run dev
```

(First time on a new machine: `npm install` and `copy .env.local.example .env.local` first.)

Open <http://localhost:3000>. On the login page click **Use demo account** (it only fills in the fields), then **Log in**.

## Using the app

Log in with **demo@gapfinder.ai / demo123** (on the login page: **Use demo account**, then **Log in**).

### 1. Upload — your material lives in four folders

1. Open **Upload**. Under **1. Choose a folder** pick Syllabus, Notes, Textbook or Past paper.
2. Under **2. Choose a file** pick a PDF or .txt, then click **Save to <folder> folder**.
3. Under **Your material** each folder lists its files. The **three-dot menu (⋯)** next to a
   file offers **View details**, **Rename** and **Delete**. The menu next to a folder offers
   **View details** and **Delete all files**. Deleting asks for confirmation first, because it
   also removes what was built from the file (its quiz questions, or a syllabus's topic map).

### 2. Topic Map — build, review, save

1. Open **Topic Map** and choose a file from the Syllabus folder.
2. Optional: **Open file content** to read the file.
3. Click **Topic Build**. It extracts the subject and its topics and shows them for review
   (nothing is saved yet). You can rename the subject or remove topics.
4. Click **Save topic map**. This links your notes to each topic and maps past-paper
   questions (about 30-60 seconds on the free AI tier).
5. The syllabus now appears under **SYLLABI** in the sidebar (for example *Physics Syllabus*).
   Click it to open that syllabus's page, with **Quiz me** and **Ask** links on every topic.

### 3. Quiz and tutor — built from the saved syllabus

- **Quiz**: pick a topic (grouped by syllabus) and generate. Questions come from the notes
  linked to that topic, and each cites its chapter and page.
- **Explain**: ask a question, optionally focused on a topic. The tutor searches that topic's
  material and gets your saved syllabus outline as context, so it answers at the right level
  and says which topic the question belongs to. It still only answers from your notes.

Then **Gap Report**, **Plan** and **Dashboard** as before.

## How the AI part is configured (`backend/.env`)

| Setting | Current value | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `openai_compatible` | Use Gemini through its OpenAI-style API instead of Anthropic |
| `LLM_API_KEY` | your Gemini key | Free, from Google AI Studio |
| `LLM_MODEL` | list of 5 Gemini models, best first | Tried in order; moves to the next when one hits its daily cap or is overloaded. Put stronger models first: the weakest one occasionally answers "not covered" wrongly. |
| `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | Gemini / `gemini-embedding-001` | Free embeddings at 1536 dimensions (matches the DB) |
| `OPENAI_API_KEY` | not used | Safe to delete; the OpenAI account has no credit |

To switch back to Claude later: `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-sonnet-5`,
add `ANTHROPIC_API_KEY=...`.

## If something goes wrong

| Symptom | Cause / fix |
|---|---|
| "All configured models are unavailable… quota" | Gemini free tier allows ~20 requests/day **per model**. Wait for the daily reset, or add more model names to `LLM_MODEL`, or use a second free key (Groq: see comments in `.env`). |
| 503 "model is experiencing high demand" | Google overload; the app already tries the next model. Retry in a minute. |
| Saving a big syllabus, or uploading a long textbook, is slow | Texts are embedded in batches of 50, and the free Gemini tier allows about 100 embeddings per minute, so the app pauses ~25 s when it hits the limit and retries. A 120-topic syllabus took about 3 minutes. Just wait; nothing is lost if it fails. |
| Topic Build / Save fails with 503 or "quota" | Same Gemini free-tier limit as above. Wait, or add models to `LLM_MODEL`. Nothing is half-saved: a failed Save changes nothing. |
| Login says invalid / network error | Backend not running — start Terminal 1. |
| `password authentication failed` on startup | `DATABASE_URL` password wrong. Remove the `[ ]` brackets around the password and percent-encode `@ : / ? # `. |
| Hangs on database connect | You're on port **6543** (Transaction pooler). Use **5432** (Session pooler). |
| `Port 3000 is in use` / Next lock error | A previous dev server is still running: close that terminal, or `taskkill /F /IM node.exe`. |
| PDF upload errors | PyMuPDF can't load on this PC (missing Windows C++ runtime); the app falls back to `pdfplumber` automatically. Installing the "Microsoft Visual C++ Redistributable (x64)" restores the faster path. |

## Security notes before showing this publicly

- Change `JWT_SECRET` (it signs login tokens) — already done locally; use a fresh one in any deployment.
- The demo password `demo123` is intentional for judges; don't ship it to anything real.
- `backend/.env` holds your database password and API key. It is git-ignored; never paste it into chat or commit it.
