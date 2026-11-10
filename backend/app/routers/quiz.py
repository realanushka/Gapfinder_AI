import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.chunk import Chunk
from app.models.chunk_topic import ChunkTopic
from app.models.document import Document
from app.models.question import Question
from app.models.topic import Topic
from app.models.user import User
from app.schemas.quiz import QuestionResponse, QuizGenerationRequest
from app.services.gap_report_service import diagnose_topics
from app.services.quiz_service import (
    answer_is_grounded,
    generate_mcq_from_chunk,
    generate_short_answer_from_chunk,
    questions_for_topic,
    validate_mcq,
)

router = APIRouter(prefix="/quiz", tags=["quiz"])

# Topics to cover when no topic is given (a weak-weighted retake).
RETAKE_TOPIC_COUNT = 3


def format_citation(chunk: Chunk | None) -> str | None:
    """Build "Chapter 3, Section 3.2, p. 45" from the chunk's stored metadata.

    This is what makes every question traceable back to the student's own
    material (Plan Step 5.3), so it is assembled server-side rather than left
    to the client.
    """
    if chunk is None:
        return None
    parts = [part for part in (chunk.chapter, chunk.section) if part]
    if chunk.page is not None:
        parts.append(f"p. {chunk.page}")
    return ", ".join(parts) or None


def to_response(question: Question, chunk: Chunk | None) -> QuestionResponse:
    return QuestionResponse(
        id=question.id,
        topic_id=question.topic_id,
        question=question.question,
        options=question.options,
        source_chunk_id=question.source_chunk_id,
        citation=format_citation(chunk),
    )


async def _chunks_for_topic(db: AsyncSession, topic_id: uuid.UUID) -> list[Chunk]:
    chunk_ids = list(
        (
            await db.scalars(
                select(ChunkTopic.chunk_id).where(ChunkTopic.topic_id == topic_id)
            )
        ).all()
    )
    if not chunk_ids:
        return []
    return list((await db.scalars(select(Chunk).where(Chunk.id.in_(chunk_ids)))).all())


async def _already_used_chunk_ids(db: AsyncSession, topic_id: uuid.UUID) -> set[uuid.UUID]:
    """Chunks this topic has already produced questions from.

    A retake should ask *new* questions (Step 10.1), so previously used chunks
    go to the back of the queue rather than being drawn again first.
    """
    return set(
        (
            await db.scalars(
                select(Question.source_chunk_id).where(Question.topic_id == topic_id)
            )
        ).all()
    )


async def _generate_for_topic(
    db: AsyncSession, topic: Topic, limit: int | None = None
) -> list[tuple[Question, Chunk]]:
    chunks = await _chunks_for_topic(db, topic.id)
    if not chunks:
        return []

    # Where this topic sits in the syllabus, so questions target the right area.
    subject = (
        await db.scalar(select(Document.subject).where(Document.id == topic.document_id))
        if topic.document_id is not None
        else None
    )

    used = await _already_used_chunk_ids(db, topic.id)
    # Unused chunks first so repeat quizzes cover fresh material.
    chunks.sort(key=lambda chunk: chunk.id in used)

    wanted = limit if limit is not None else questions_for_topic(topic.exam_weight)
    selected = chunks[:wanted]

    pairs: list[tuple[Question, Chunk]] = []
    for index, chunk in enumerate(selected):
        # Mostly MCQs because they grade without an LLM; one short answer per
        # topic to test recall rather than recognition (Step 5.4).
        is_short_answer = index == len(selected) - 1 and len(selected) >= 3

        try:
            if is_short_answer:
                generated = await generate_short_answer_from_chunk(chunk.text, subject, topic.name)
                answer = str(generated.get("answer", ""))
                if not answer_is_grounded(chunk.text, answer):
                    continue
                options = None
                correct = answer
            else:
                generated = await generate_mcq_from_chunk(chunk.text, subject, topic.name)
                options = generated.get("options")
                answer_key = str(generated.get("answer", ""))
                if not options or not validate_mcq(chunk.text, options, answer_key):
                    continue
                correct = answer_key
        except (KeyError, ValueError, TypeError):
            # A malformed generation is dropped, never surfaced as a question.
            continue

        question = Question(
            topic_id=topic.id,
            question=generated["question"],
            options=options,
            correct_answer=correct,
            source_chunk_id=chunk.id,
            explanation=generated.get("explanation"),
        )
        db.add(question)
        pairs.append((question, chunk))

    return pairs


@router.post("/generate", response_model=list[QuestionResponse])
async def generate_quiz(
    payload: QuizGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuestionResponse]:
    """Generate a quiz for one topic, or a weak-weighted retake across topics.

    With `topic_id` omitted this picks the weakest topics (Step 10.1); the
    number of questions per topic scales with that topic's exam weight.
    """
    if payload.topic_id is not None:
        topic = await db.get(Topic, payload.topic_id)
        if topic is None or topic.user_id != current_user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")
        targets = [topic]
    else:
        # Weakest first; diagnoses are already sorted by score ascending.
        diagnoses = await diagnose_topics(db, current_user.id, with_reasons=False)
        topic_ids = [d.topic_id for d in diagnoses[:RETAKE_TOPIC_COUNT]]
        if not topic_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "No scored topics yet — take a quiz on a specific topic first",
            )
        targets = list(
            (await db.scalars(select(Topic).where(Topic.id.in_(topic_ids)))).all()
        )

    pairs: list[tuple[Question, Chunk]] = []
    for topic in targets:
        pairs.extend(await _generate_for_topic(db, topic, payload.num_questions))

    if not pairs:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No material is linked to that topic yet — build the topic map after "
            "uploading notes or a textbook",
        )

    await db.commit()
    for question, _ in pairs:
        await db.refresh(question)

    return [to_response(question, chunk) for question, chunk in pairs]


@router.get("/topic/{topic_id}", response_model=list[QuestionResponse])
async def list_questions_for_topic(
    topic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuestionResponse]:
    rows = await db.execute(
        select(Question, Chunk)
        .join(Chunk, Chunk.id == Question.source_chunk_id)
        .where(Question.topic_id == topic_id)
    )
    return [to_response(question, chunk) for question, chunk in rows.all()]
