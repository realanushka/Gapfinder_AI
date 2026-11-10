# REMAINING.md — what is left

**The project is complete and running.** See [RUNNING.md](./RUNNING.md) to start it.
Everything below is optional polish, in rough priority order.

## Things to know about the free LLM tier

- Gemini's free tier allows about **20 requests per day per model**. The app lists
  several models in `LLM_MODEL` and moves to the next automatically, but a heavy
  day of testing can still exhaust them. Fix: wait for the daily reset, add a second
  free provider (Groq, see comments in `backend/.env`), or enable billing on Google.
- *Build from syllabus* took ~3 minutes on the demo paper (one slow LLM call per past question).

## Optional improvements

| Item | Why | Size |
|---|---|---|
| Run past-paper topic matching in parallel / in the background | 40-question papers would time out on the free tier | Medium |
| Redirect to login when the JWT expires | Currently shows an error | Small |
| Smarter heading detection in `detect_structure()` | Unusual syllabus formats won't split into chapters | Small |
| Automated tests (scoring, past-paper splitter, grounding check) | None exist; all verified by hand | Medium |
| Install the Microsoft Visual C++ Redistributable | Restores faster PyMuPDF; pdfplumber fallback is used now | Trivial |
| Delete unused `OPENAI_API_KEY` from `.env` | OpenAI account has no credit and is not used | Trivial |
| Rotate secrets before any public deployment | `JWT_SECRET`, DB password; demo password `demo123` is intentional | Trivial |
