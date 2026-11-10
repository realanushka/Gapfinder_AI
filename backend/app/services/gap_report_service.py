"""Score topics, classify mastery, write the diagnosis (Plan Step 7)."""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import Attempt
from app.models.question import Question
from app.models.topic import Topic
from app.models.topic_score import MasteryStatus
from app.services.llm_client import generate_text

WEAK_THRESHOLD = 0.5
STRONG_THRESHOLD = 0.75

REASON_SYSTEM_PROMPT = """You write a one-line diagnosis of why a student is weak in a topic,
based on their wrong answers and the concepts they missed. Be specific and concise, e.g.
"You got 3 of 4 questions on photosynthesis wrong, mostly about the light reaction."
Write one sentence only, addressed to the student as "you"."""


@dataclass
class TopicDiagnosis:
    topic_id: uuid.UUID
    topic_name: str
    exam_weight: int
    score: float
    status: MasteryStatus
    total_answered: int
    wrong_count: int
    concept_tags: list[str] = field(default_factory=list)
    reason: str = ""


def compute_topic_score(earned: float, total_count: int) -> float:
    """score = earned / total, where a partial answer contributes a fraction."""
    if total_count == 0:
        return 0.0
    return max(0.0, min(1.0, earned / total_count))


def classify_status(score: float) -> MasteryStatus:
    if score < WEAK_THRESHOLD:
        return MasteryStatus.WEAK
    if score < STRONG_THRESHOLD:
        return MasteryStatus.MEDIUM
    return MasteryStatus.STRONG


async def generate_reason(
    topic_name: str, wrong_answers: list[str], concept_tags: list[str]
) -> str:
    prompt = (
        f"Topic: {topic_name}\n"
        f"Questions answered wrongly: {wrong_answers}\n"
        f"Concepts missed: {concept_tags}"
    )
    return (await generate_text(REASON_SYSTEM_PROMPT, prompt)).strip()


async def diagnose_topics(
    db: AsyncSession, user_id: uuid.UUID, with_reasons: bool = True
) -> list[TopicDiagnosis]:
    """Score every topic the user has actually answered questions on.

    Scores are pure arithmetic over stored attempts -- no LLM involved -- so the
    numbers stay reproducible. The LLM only writes the prose reason.
    """
    topics = list(
        (await db.scalars(select(Topic).where(Topic.user_id == user_id))).all()
    )

    diagnoses: list[TopicDiagnosis] = []

    for topic in topics:
        rows = (
            await db.execute(
                select(Attempt, Question)
                .join(Question, Question.id == Attempt.question_id)
                .where(Question.topic_id == topic.id, Attempt.user_id == user_id)
                .order_by(Attempt.timestamp)
            )
        ).all()

        if not rows:
            continue

        # Only the latest attempt per question counts, so a retake reflects
        # current knowledge instead of averaging in earlier mistakes.
        latest: dict[uuid.UUID, tuple[Attempt, Question]] = {}
        for attempt, question in rows:
            latest[question.id] = (attempt, question)

        earned = sum(attempt.score for attempt, _ in latest.values())
        wrong = [
            (attempt, question)
            for attempt, question in latest.values()
            if not attempt.is_correct
        ]

        score = compute_topic_score(earned, len(latest))
        diagnoses.append(
            TopicDiagnosis(
                topic_id=topic.id,
                topic_name=topic.name,
                exam_weight=topic.exam_weight,
                score=score,
                status=classify_status(score),
                total_answered=len(latest),
                wrong_count=len(wrong),
                concept_tags=sorted(
                    {attempt.concept_tag for attempt, _ in wrong if attempt.concept_tag}
                ),
            )
        )

        if with_reasons:
            diagnoses[-1].reason = (
                await generate_reason(
                    topic.name,
                    [question.question for _, question in wrong][:5],
                    diagnoses[-1].concept_tags,
                )
                if wrong
                else f"You answered all {len(latest)} questions on {topic.name} correctly."
            )

    # Weakest first: that is the order the student should revise in.
    diagnoses.sort(key=lambda d: d.score)
    return diagnoses
