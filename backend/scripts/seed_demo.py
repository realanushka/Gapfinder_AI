"""Seed the demo account so judges can explore without uploading anything.

    python -m scripts.seed_demo

Deliberately does NOT call the LLM: the topic tree, questions and prior attempts
are written out in scripts/demo_data.py, so the demo works with no API keys and
is identical every run. Chunk embeddings are the one exception -- they need the
embedding API, so if OPENAI_API_KEY is absent the script seeds everything else
and warns that the Explain assistant will have nothing to retrieve.

Safe to re-run: it clears the demo user's data first, then rebuilds it.
"""

import asyncio
import sys

from sqlalchemy import delete, select

from app.config import get_settings
from app.core.security import hash_password
from app.database import AsyncSessionLocal, engine
from app.models.attempt import Attempt
from app.models.chunk import Chunk
from app.models.chunk_topic import ChunkTopic
from app.models.document import Document, DocumentType
from app.models.past_question import PastQuestion
from app.models.plan import Plan
from app.models.question import Question
from app.models.topic import Topic
from app.models.topic_score import TopicScore
from app.models.user import User
from app.services.gap_report_service import classify_status
from app.services.topic_service import split_past_paper
from scripts import demo_data

settings = get_settings()


async def main() -> int:
    async with AsyncSessionLocal() as db:
        # --- user -----------------------------------------------------------
        user = await db.scalar(select(User).where(User.email == settings.demo_user_email))
        if user is None:
            user = User(
                name="Demo Student",
                email=settings.demo_user_email,
                password_hash=hash_password(settings.demo_user_password),
            )
            db.add(user)
            await db.flush()
            print(f"[+] created demo user {settings.demo_user_email}")
        else:
            # Wipe prior demo content so re-running is idempotent. Documents
            # cascade to chunks; topics cascade to questions and topic_scores.
            await db.execute(delete(Attempt).where(Attempt.user_id == user.id))
            await db.execute(delete(TopicScore).where(TopicScore.user_id == user.id))
            await db.execute(delete(Plan).where(Plan.user_id == user.id))
            await db.execute(delete(Topic).where(Topic.user_id == user.id))
            await db.execute(delete(Document).where(Document.user_id == user.id))
            await db.flush()
            print(f"[~] reset existing demo user {settings.demo_user_email}")

        # --- documents and chunks -------------------------------------------
        syllabus = Document(
            user_id=user.id,
            type=DocumentType.SYLLABUS,
            filename="class10_science_syllabus.txt",
            subject="Class 10 Science",  # a saved topic map -> sidebar shortcut
        )
        notes = Document(
            user_id=user.id, type=DocumentType.NOTES, filename="life_processes_notes.txt"
        )
        paper = Document(
            user_id=user.id, type=DocumentType.PAST_PAPER, filename="science_board_2023.txt"
        )
        db.add_all([syllabus, notes, paper])
        await db.flush()

        db.add(
            Chunk(
                document_id=syllabus.id,
                text=demo_data.SYLLABUS_TEXT,
                chapter="Unit 2",
                section="Life Processes",
                page=1,
            )
        )
        db.add(
            Chunk(
                document_id=paper.id,
                text=demo_data.PAST_PAPER_TEXT,
                chapter="Board Paper 2023",
                section=None,
                page=1,
            )
        )

        note_chunks: list[Chunk] = []
        for chapter, section, page, text in demo_data.NOTES_CHUNKS:
            chunk = Chunk(
                document_id=notes.id, text=text, chapter=chapter, section=section, page=page
            )
            db.add(chunk)
            note_chunks.append(chunk)
        await db.flush()

        # --- embeddings (optional) ------------------------------------------
        if settings.embeddings_configured:
            from app.services.embedding_client import embed_texts

            vectors = await embed_texts([chunk.text for chunk in note_chunks])
            for chunk, vector in zip(note_chunks, vectors, strict=True):
                chunk.embedding = vector
            print(f"[+] embedded {len(note_chunks)} note chunks")
        else:
            print(
                "[!] OPENAI_API_KEY not set — chunks seeded without embeddings.\n"
                "    Quiz, gap report, plan and dashboard will work; the Explain\n"
                "    assistant will find nothing until you re-run with a key."
            )

        # --- topics ----------------------------------------------------------
        topics_by_name: dict[str, Topic] = {}
        for name, subtopic_names in demo_data.TOPIC_TREE:
            parent = Topic(user_id=user.id, name=name, exam_weight=0, document_id=syllabus.id)
            db.add(parent)
            await db.flush()
            topics_by_name[name] = parent

            for subtopic_name in subtopic_names:
                db.add(
                    Topic(
                        user_id=user.id,
                        name=subtopic_name,
                        parent_id=parent.id,
                        exam_weight=0,
                        document_id=syllabus.id,
                    )
                )
        await db.flush()

        # --- link material to topics -----------------------------------------
        # Mirrors what the real pipeline does by vector search; here the mapping
        # is fixed so the demo is deterministic.
        topic_for_chunk = {
            0: "Nutrition",
            1: "Nutrition",
            2: "Respiration",
            3: "Respiration",
            4: "Transportation",
            5: "Transportation",
        }
        for index, chunk in enumerate(note_chunks):
            db.add(
                ChunkTopic(chunk_id=chunk.id, topic_id=topics_by_name[topic_for_chunk[index]].id)
            )

        # --- past questions and exam weights ---------------------------------
        paper_questions = split_past_paper(demo_data.PAST_PAPER_TEXT)
        # Q1-Q3 nutrition, Q4-Q5 respiration, Q6 transportation.
        paper_topics = [
            "Nutrition",
            "Nutrition",
            "Nutrition",
            "Respiration",
            "Respiration",
            "Transportation",
        ]
        weights: dict[str, int] = {}
        for text, topic_name in zip(paper_questions, paper_topics, strict=False):
            db.add(
                PastQuestion(
                    text=text,
                    topic_id=topics_by_name[topic_name].id,
                    year=2023,
                    document_id=paper.id,
                )
            )
            weights[topic_name] = weights.get(topic_name, 0) + 1

        for name, count in weights.items():
            topics_by_name[name].exam_weight = count

        # --- questions, attempts and score history ---------------------------
        total_attempts = 0
        for topic_name, specs in demo_data.QUESTIONS.items():
            topic = topics_by_name[topic_name]
            questions: list[Question] = []

            for text, options, correct, explanation, chunk_index in specs:
                question = Question(
                    topic_id=topic.id,
                    question=text,
                    options=options,
                    correct_answer=correct,
                    source_chunk_id=note_chunks[chunk_index].id,
                    explanation=explanation,
                )
                db.add(question)
                questions.append(question)
            await db.flush()

            scores = demo_data.ATTEMPT_SCORES[topic_name]
            reasons = demo_data.ATTEMPT_REASONS[topic_name]

            for attempt_index, fraction in enumerate(scores, start=1):
                db.add(
                    TopicScore(
                        user_id=user.id,
                        topic_id=topic.id,
                        attempt_no=attempt_index,
                        score=fraction,
                        status=classify_status(fraction),
                        reason=reasons[attempt_index - 1],
                    )
                )

            # Attempt rows for the final sitting only, so the live gap report
            # agrees with the last snapshot.
            correct_count = round(scores[-1] * len(questions))
            for position, question in enumerate(questions):
                was_right = position < correct_count
                db.add(
                    Attempt(
                        user_id=user.id,
                        question_id=question.id,
                        student_answer=question.correct_answer if was_right else "(incorrect)",
                        is_correct=was_right,
                        score=1.0 if was_right else 0.0,
                        feedback=question.explanation,
                        concept_tag=None if was_right else "light reaction",
                    )
                )
                total_attempts += 1

        await db.commit()

    await engine.dispose()

    print(
        f"[+] seeded 3 documents, {len(demo_data.NOTES_CHUNKS)} note chunks, "
        f"{sum(1 + len(s) for _, s in demo_data.TOPIC_TREE)} topics, "
        f"{len(paper_questions)} past questions, {total_attempts} attempts, "
        "3 score snapshots per topic"
    )
    print(f"\nLog in as {settings.demo_user_email} / {settings.demo_user_password}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
