"""Diagnostic quiz generation and validation (Plan Step 5)."""

import re

from app.services.llm_client import generate_json
from app.services.schemas import MCQ_SCHEMA, SHORT_ANSWER_SCHEMA

MCQ_SYSTEM_PROMPT = """You write one multiple-choice question using ONLY the provided text.
Never use outside knowledge. The correct option must be stated in the text, using wording
taken from it. Any "Subject" / "Syllabus topic" lines only say which part of the
curriculum the question is for; they are not facts to use. Return ONLY JSON:
{"question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
"answer": "A", "explanation": "..."}"""

SHORT_ANSWER_SYSTEM_PROMPT = """You write one short-answer question using ONLY the provided
text, answerable in one or two sentences. Never use outside knowledge. Return ONLY JSON:
{"question": "...", "answer": "...", "explanation": "..."}"""

# Questions per topic: 2 baseline, up to 4 as exam weight rises (Step 5.1).
MIN_QUESTIONS_PER_TOPIC = 2
MAX_QUESTIONS_PER_TOPIC = 4

STOPWORDS = {
    "the", "a", "an", "of", "and", "or", "to", "in", "is", "are", "was", "were",
    "it", "its", "this", "that", "for", "on", "by", "with", "as", "at", "from",
}


def questions_for_topic(exam_weight: int) -> int:
    """More questions for topics that carry more exam weight."""
    return min(MAX_QUESTIONS_PER_TOPIC, MIN_QUESTIONS_PER_TOPIC + max(0, exam_weight))


def _with_curriculum(chunk_text: str, subject: str | None, topic: str | None) -> str:
    """Prefix the source text with where it sits in the student's syllabus.

    The header only steers the question toward the right curriculum area; the
    system prompts still require the question and answer to come from the text.
    """
    header = []
    if subject:
        header.append(f"Subject: {subject}")
    if topic:
        header.append(f"Syllabus topic: {topic}")
    if not header:
        return chunk_text
    return "\n".join(header) + "\n\nSource text:\n" + chunk_text


async def generate_mcq_from_chunk(
    chunk_text: str, subject: str | None = None, topic: str | None = None
) -> dict:
    """Schema-constrained, so `options` always has A-D and `answer` is one of them."""
    return await generate_json(
        MCQ_SYSTEM_PROMPT, _with_curriculum(chunk_text, subject, topic), schema=MCQ_SCHEMA
    )


async def generate_short_answer_from_chunk(
    chunk_text: str, subject: str | None = None, topic: str | None = None
) -> dict:
    return await generate_json(
        SHORT_ANSWER_SYSTEM_PROMPT,
        _with_curriculum(chunk_text, subject, topic),
        schema=SHORT_ANSWER_SCHEMA,
    )


def _content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word for word in words if word not in STOPWORDS and len(word) > 2}


def answer_is_grounded(chunk_text: str, answer_text: str, threshold: float = 0.6) -> bool:
    """Check the answer actually comes from the source chunk (Step 5.2).

    An exact substring test is too brittle -- the model legitimately rephrases --
    so this requires most of the answer's content words to appear in the chunk.
    Anything below the threshold is discarded rather than shown to the student.
    """
    answer_words = _content_words(answer_text)
    if not answer_words:
        return False
    overlap = answer_words & _content_words(chunk_text)
    return len(overlap) / len(answer_words) >= threshold


def validate_mcq(chunk_text: str, options: dict, answer_key: str) -> bool:
    correct = options.get(answer_key)
    if not correct:
        return False
    return answer_is_grounded(chunk_text, str(correct))
