# DEPLOYING.md — putting GapFinder AI live

This guide deploys the app for free on three services:

| Part | Service | What it hosts |
|---|---|---|
| Database | **Supabase** (already set up) | Postgres + pgvector: users, files, topics, embeddings |
| Backend | **Render** (free web service) | FastAPI app in `backend/` |
| Frontend | **Vercel** (free hobby plan) | Next.js app in `frontend/` |

```
Browser ──► Vercel (Next.js) ──► Render (FastAPI) ──► Supabase (Postgres + pgvector)
                                        └──────────► Gemini API (LLM + embeddings)
```

Uploaded files are parsed in memory and their text is stored in the database,
so the backend needs no persistent disk. That's why Render's free tier works.

Deploy in this order: **database → backend → frontend → connect them.** The
frontend needs the backend URL, and the backend needs the frontend URL for CORS.

---

## 0. Before you start

1. Accounts: GitHub, [Render](https://render.com), [Vercel](https://vercel.com).
   Sign in to both with GitHub.
2. Push the latest code:

   ```powershell
   cd "D:\GapFinder AI"
   git status            # .env files and venv/node_modules must NOT be listed
   git add .
   git commit -m "Prepare for deployment"
   git push
   ```

   If `git status` lists `.env` (or any `.env` file other than `.env.example`),
   stop: they hold secrets. The root `.gitignore` should exclude them. If one was
   committed earlier, run `git rm --cached <file>`, commit, and **rotate the
   secrets it contained** (DB password, Gemini key, JWT secret).

3. Keep the root `.env` open. You'll copy values from it in steps 2 and 3.

---

## 1. Database (Supabase)

The tables and demo data already exist in your Supabase project, so the deployed
backend can use the **same** database. Check two things:

1. **Connection string:** in Supabase, go to **Project Settings → Database → Connection
   string**, choose **Session pooler**, **port 5432**. Do not use 6543, the
   Transaction pooler, which makes asyncpg hang. This is the same `DATABASE_URL` as
   in the root `.env`.
2. **Schema is current:** run this locally whenever a new migration is added:

   ```powershell
   cd "D:\GapFinder AI\backend"
   .\venv\Scripts\Activate.ps1
   alembic upgrade head
   python -m scripts.seed_demo     # safe to re-run
   ```

> Supabase's free tier **pauses a project after 7 days without activity**. Before
> a demo, open the Supabase dashboard and click **Restore** if it's paused.

---

## 2. Backend (Render)

1. On Render, click **New → Web Service** and connect your GitHub repo.
2. Settings:

   | Field | Value |
   |---|---|
   | Name | `gapfinder-api` (this becomes part of the URL) |
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | Free |

3. **Environment Variables** (click *Add Environment Variable* for each). Copy
   the values from the root `.env` unless noted otherwise:

   | Key | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.11.9`. The app was tested on 3.11, and Render's newer default may fail to build the pinned packages |
   | `DATABASE_URL` | from `.env` (Session pooler, port 5432) |
   | `JWT_SECRET` | **a new random value** (see below), not the local one |
   | `JWT_ALGORITHM` | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
   | `LLM_PROVIDER` | `openai_compatible` |
   | `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` |
   | `LLM_API_KEY` | your Gemini key |
   | `LLM_MODEL` | same comma-separated model list as in `.env` |
   | `EMBEDDING_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` |
   | `EMBEDDING_MODEL` | `gemini-embedding-001` |
   | `EMBEDDING_DIM` | `1536` |
   | `ENVIRONMENT` | `production` |
   | `CORS_ORIGINS` | `http://localhost:3000` for now. You'll replace it in step 4 |
   | `DEMO_USER_EMAIL` | `demo@gapfinder.ai` |
   | `DEMO_USER_PASSWORD` | `demo123` |

   Generate a JWT secret locally:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

4. Click **Create Web Service** and watch the logs. The first build takes a few
   minutes.
5. When it shows **Live**, test it (use your own URL):

   - `https://gapfinder-api.onrender.com/health` should return `{"status":"ok"}`
   - `https://gapfinder-api.onrender.com/docs` should show the API docs page

   Copy this base URL, **without a trailing slash**. You need it next.

> **Free-tier cold starts:** Render puts a free service to sleep after about 15
> minutes with no traffic. The next request then takes **30–60 s** to wake it.
> Before a demo, open `/health` once and wait for it to respond.

---

## 3. Frontend (Vercel)

1. On Vercel, click **Add New → Project** and import the same GitHub repo.
2. Settings:

   | Field | Value |
   |---|---|
   | Framework Preset | Next.js (auto-detected) |
   | Root Directory | `frontend` (click *Edit* and select it) |
   | Build / Install / Output | leave the defaults (`next build`, `npm install`) |

3. **Environment Variables:**

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | your Render URL, e.g. `https://gapfinder-api.onrender.com` (no trailing slash) |

4. Click **Deploy**. When it finishes you get a URL such as
   `https://gapfinder-ai.vercel.app`. Copy it.

> `NEXT_PUBLIC_*` variables are **built into the JavaScript at build time**. If you
> change `NEXT_PUBLIC_API_URL` later, you must **redeploy** the frontend
> (Deployments → ⋯ → Redeploy) for the change to apply.

---

## 4. Connect them (CORS)

The backend accepts browser requests only from origins listed in `CORS_ORIGINS`.

1. On Render, open **gapfinder-api → Environment** and set:

   ```
   CORS_ORIGINS=https://gapfinder-ai.vercel.app,http://localhost:3000
   ```

   - Use your exact Vercel URL, with `https://` and **no trailing slash**.
   - Separate entries with commas and no spaces. Keeping localhost lets local dev
     still work.
   - If you add a custom domain later, add it here too.

2. Save. Render redeploys the backend automatically, which takes about a minute.

---

## 5. Smoke test the live site

Open the Vercel URL and check these in order:

1. [ ] The login page loads.
2. [ ] Click **Use demo account**, then **Log in**. The dashboard opens.
3. [ ] **Upload**: a small PDF or .txt saves into a folder.
4. [ ] **Topic Map**: pick a syllabus, run **Topic Build**, then **Save topic map**.
5. [ ] **Quiz**: generate questions for a topic.
6. [ ] **Explain**: ask a question and get an answer that cites your notes.
7. [ ] **Gap Report**, **Plan** and **Dashboard** load.

If login fails, open the browser DevTools (F12) and check the **Console** and
**Network** tabs. Then use the table below.

---

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Console shows a `CORS policy` error | `CORS_ORIGINS` on Render doesn't exactly match the Vercel URL. Check `https://`, the trailing slash and typos, then save and wait for the redeploy. |
| Requests go to `localhost:8000` from the live site | `NEXT_PUBLIC_API_URL` wasn't set at build time. Set it on Vercel, then **Redeploy**. |
| First request takes about 1 minute or times out | Render cold start. Open `/health` and wait, then retry. |
| Render build fails on `asyncpg` / `pymupdf` / `pydantic-core` | `PYTHON_VERSION` is missing or too new. Set it to `3.11.9`, then **Manual Deploy → Clear build cache & deploy**. |
| Render log: `password authentication failed` | `DATABASE_URL` password is wrong. Remove any `[ ]` around it and percent-encode `@ : / ? #`. |
| Backend hangs at startup on database connect | You're using port 6543. Switch to the Session pooler on **5432**. |
| Render log: `Out of memory (used over 512Mi)` | A very large PDF was uploaded on the free tier. Upload smaller files, or upgrade to the Starter instance. |
| "All configured models are unavailable… quota" | Gemini free-tier daily cap (about 20 requests per model per day). Wait for the daily reset or add more models to `LLM_MODEL`. Note that local use and the live site **share the same key and quota**. |
| Everything fails after a week of no use | The Supabase project paused. Restore it from the dashboard. |

---

## 7. Updating the live app

Both Render and Vercel **auto-deploy on every push to `main`**:

```powershell
git add .
git commit -m "Describe the change"
git push
```

- **New database migration?** Run `alembic upgrade head` locally (step 1)
  **before** pushing, so the live backend never runs against an old schema.
- **New environment variable?** Add it on Render or Vercel. Vercel needs a
  redeploy for `NEXT_PUBLIC_*` variables.

---

## 8. Security checklist before sharing the link

- [ ] `JWT_SECRET` on Render is a fresh random value, not the local one.
- [ ] No `.env` file is in the GitHub repo. Check the repo page on github.com.
- [ ] `CORS_ORIGINS` lists only your own domains.
- [ ] The demo account `demo@gapfinder.ai / demo123` is meant for judges. Remove
      it or change its password if the app ever holds real users' data.
- [ ] Set a spending limit or budget alert on the Gemini or Google Cloud project,
      in case you move off the free tier later.

---

## Optional upgrades

- **No cold starts:** use Render's Starter plan (about $7/month), or Railway or
  Fly.io.
- **Custom domain:** add it under Vercel → Project → Settings → Domains, then
  add it to `CORS_ORIGINS` on Render.
- **Separate production database:** create a second Supabase project, put its
  URL in Render's `DATABASE_URL`, and run `alembic upgrade head` and
  `python -m scripts.seed_demo` against it by temporarily pointing your local
  `.env` at it. This keeps local testing from touching live data.
