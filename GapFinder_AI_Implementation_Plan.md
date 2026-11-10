# GapFinder AI: Step-by-Step Implementation Plan

## Step 0: Pick a simple tech stack

Choose tools that are fast to build with and easy to demo.

| Layer | Suggested choice | Why |
|---|---|---|
| Frontend | Next.js (React) + Tailwind | Fast UI, easy deployment on Vercel |
| Backend | FastAPI (Python) | Python has the best PDF and AI libraries |
| Database | PostgreSQL with **pgvector** (Supabase works well) | One database holds both normal data and embeddings |
| PDF parsing | PyMuPDF or pdfplumber | Extracts text along with page numbers |
| Embeddings | OpenAI `text-embedding-3-small`, or a free model like `bge-small` | Turns text into vectors for search |
| LLM | Claude, GPT or Gemini API | Generates questions, grades answers, writes plans |
| Charts | Recharts | For the progress dashboard |
| Auth | Supabase Auth or simple JWT | Login with demo credentials |

## Step 1: Design the database

Create these tables first, because every feature depends on them.

- **users**: id, name, email, password_hash
- **documents**: id, user_id, type (syllabus / notes / textbook / past_paper), filename
- **chunks**: id, document_id, text, chapter, section, page, embedding (vector)
- **topics**: id, user_id, name, parent_id (for subtopics), exam_weight
- **chunk_topics**: chunk_id, topic_id (which chunks belong to which topic)
- **past_questions**: id, text, topic_id, year
- **quizzes / questions**: id, topic_id, question, options, correct_answer, source_chunk_id
- **attempts / answers**: id, user_id, question_id, student_answer, is_correct, feedback, timestamp
- **topic_scores**: user_id, topic_id, attempt_no, score, status (weak/medium/strong), reason
- **plans**: user_id, plan_json, created_at

## Step 2: Build login and the basic app shell

1. Add signup and login, with protected pages.
2. Create a **demo account** (for example `demo@gapfinder.ai` / `demo123`) and preload it with sample material, so judges can explore without uploading anything.
3. Build the main pages as empty shells: Upload, Topic Map, Quiz, Gap Report, Plan, Explain, Dashboard.

## Step 3: Material upload and ingestion (the "R" in RAG)

This is the foundation of the whole app.

1. **Upload**: accept PDF or text files and tag each one as syllabus, notes, textbook or past paper.
2. **Extract** the text page by page, and keep the page numbers.
3. **Detect structure**: find chapter and section headings (lines like "Chapter 3" or "3.2 ...", or larger font sizes).
4. **Chunk** the text into pieces of about 300–500 words with a small overlap. Every chunk stores its *metadata*: document, chapter, section and page.
5. **Embed** each chunk and save the vector in the `chunks` table.

> The metadata is what makes citations like "Chapter 3, Section 2, Page 45" possible later.

## Step 4: Build the topic map

1. **Syllabus to topic tree**: send the syllabus text to the LLM and ask for strict JSON: `{topic, subtopics: [...]}`. Save it in `topics`.
2. **Link topics to material**: for each topic, embed the topic name, run a vector search over the notes and textbook chunks, and save the top matches in `chunk_topics`.
3. **Map past-paper questions**:
   - Split past papers into individual questions (with regex on "Q1", "1." and so on, or with the LLM).
   - For each question, retrieve the closest topics by embedding similarity, then let the LLM confirm the best match.
4. **Exam weight**: count how many past questions fall under each topic. More questions means the topic is more important for the exam.
5. **UI**: show the topic tree with an "exam frequency" badge on each topic.

## Step 5: Generate the diagnostic quiz

1. Pick 2–4 questions per topic, with more for topics that carry high exam weight.
2. For each question:
   - **Retrieve** the chunks linked to that topic.
   - **Generate**: give the LLM *only those chunks* with a strict prompt: "Create one MCQ using ONLY this text. Return JSON with question, options, answer, explanation and source_chunk_id."
   - **Validate**: run a second quick check (an LLM call or a keyword match) that the answer really appears in the chunk. Throw away any question that fails.
3. Show each question with its **citation**, for example "📖 Chapter 3, Section 2, p. 45".
4. Use mostly MCQs, which are easy to grade, and add a few short-answer questions.

## Step 6: Evaluate answers and explain them

1. **MCQs**: grade them directly by comparing the student's choice with the correct answer. No AI is needed for the grading itself.
2. **Short answers**: send the LLM the question, the student's answer and the *source chunk*. Ask for JSON with `correct / partial / wrong`, a score and the reason.
3. **Explanation**: for every question, show why the right answer is right and why the student's answer was wrong, with the citation.
4. **Concept tag**: also ask the LLM to tag *which concept* inside the topic was missed (for example "light reaction"). This makes the gap report reasons specific.

## Step 7: Produce the gap report (the main output)

1. **Score each topic**: `score = correct ÷ total` (or the average for partial answers).
2. **Classify**:
   - 🔴 Weak: below 50%
   - 🟡 Medium: 50–75%
   - 🟢 Strong: above 75%
3. **Write the reason**: give the LLM the wrong answers and concept tags for that topic and ask for a one-line diagnosis, for example: *"You got 3 of 4 questions on photosynthesis wrong, mostly about the light reaction."*
4. **UI**: show colour-coded topic cards, sorted weakest first, each with its reason, its exam weight and a "Revise this" button.

## Step 8: Generate the personalized revision plan

1. **Input**: the student enters their available time, for example "5 days, 2 hours a day".
2. **Priority score**, calculated with plain code rather than AI so it is explainable:
   `priority = (1 − mastery) × exam_weight`
3. **Schedule** with code: sort topics by priority and give more time to weak topics (for example weak 45 min, medium 25 min, strong 10 min of review) until each day is full.
4. **Describe each task** with the LLM: "Read Ch 3.2 (p. 45–48), then take a 5-question mini-quiz." Each task links to the source sections.
5. **Auto-update**: after every new quiz, recalculate the topic scores and regenerate the plan. Show what changed, for example "Algebra moved from Weak to Medium ✅".

## Step 9: Build the "Explain this topic" assistant

1. The student asks a question or clicks "Explain" on a topic.
2. **Retrieve** the top 4–6 chunks from *their* uploaded material.
3. **Generate** with a strict prompt: "Answer ONLY using the context below. Cite the sources. If the answer is not in the context, say *'This isn't covered in your uploaded material.'*"
4. Show the answer with clickable citations.
5. Test it with an off-topic question to prove that it refuses. This is a strong point to show in the demo.

## Step 10: Build the re-test loop and progress dashboard

1. Add a **"Retake quiz"** button that generates *new* questions, weighted toward the weak topics.
2. Save every attempt in `topic_scores` with its attempt number.
3. Add a **dashboard** with:
   - a line chart of each topic's score across attempts (for example Algebra: 40% → 60% → 75%)
   - the overall readiness percentage
   - the number of topics that moved from weak to strong

## Step 11: Explain where retrieval and generation happen

The problem statement asks for this directly. Add an "How it works" page and an architecture diagram:

| Step | Retrieval (looks up the student's material) | Generation (LLM writes) |
|---|---|---|
| Topic map | Matches chunks and past questions to topics | Extracts topics from the syllabus |
| Quiz | Fetches the chunks for a topic | Writes questions from those chunks only |
| Evaluation | Fetches the source chunk | Explains right or wrong |
| Gap report | None (scores are calculated in code) | Writes the reason text |
| Plan | None (priority is calculated in code) | Writes the task descriptions |
| Explain | Fetches the top chunks | Answers from those chunks only |

**How the two are kept separate:** the LLM never sees anything except the retrieved chunks, every output carries a `source_chunk_id`, generated questions are validated against their source, and all scores and priorities are calculated with code rather than by the AI.

## Step 12: Test, polish and prepare the demo

1. Use one real subject (for example a Class 10 Science chapter, its syllabus and two past papers) as the demo data.
2. Pre-load the demo account with **two or three quiz attempts**, so the dashboard already shows improvement.
3. Rehearse the demo flow:
   **Upload → Topic Map → Quiz → Gap Report → Plan → Explain → Retake → Plan updates → Dashboard**
4. Deploy the frontend on Vercel and the backend on Render or Railway.
5. Prepare a slide with the architecture diagram and the retrieval vs generation table.

## Suggested build order (if time is short)

1. **Must have:** Steps 1–7. Upload, topic map, quiz with citations, evaluation and the gap report form the core diagnosis.
2. **Should have:** Steps 8–10. The plan, the explain assistant and the dashboard.
3. **Nice to have:** teacher view, spaced repetition and multiple subjects.

---

## Short summary: what is this project?

GapFinder AI is a **"doctor for studying."** Students usually revise everything equally and still miss their weak spots, because they can't ask about gaps they don't know they have. In this app, a student uploads their syllabus, notes and past papers. The app then:

1. **Tests** them with quiz questions made only from their own material, with citations.
2. **Diagnoses** which topics are weak 🔴, medium 🟡 or strong 🟢, and explains why.
3. **Prescribes** a revision plan that puts the weakest and most exam-important topics first and fits the student's available time.
4. **Updates** the plan every time the student re-tests and improves.

It uses **RAG**, so every question and explanation comes from the student's own book rather than the AI's memory. The core loop is **Upload → Test → Find weak spots → Plan → Re-test → Plan updates**, and the main output is a diagnosis, not just answers.
