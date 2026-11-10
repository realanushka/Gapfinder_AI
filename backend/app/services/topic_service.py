"""Syllabus -> topic tree, topic<->material linking, exam weighting (Plan Step 4)."""

import re

from app.services.llm_client import generate_json
from app.services.schemas import PAST_QUESTION_TOPIC_SCHEMA, TOPIC_TREE_SCHEMA

TOPIC_TREE_SYSTEM_PROMPT = """You convert an exam syllabus into a strict JSON topic tree.
Return ONLY JSON of the form:
{"subject": "...", "topics": [{"topic": "...", "subtopics": ["...", "..."]}]}.
"subject" is the school subject the syllabus covers, in one or two words (for example
"Physics" or "Class 10 Science"). Do not invent topics that are not present in the
syllabus text."""

PAST_QUESTION_TOPIC_SYSTEM_PROMPT = """You confirm which topic a past exam question belongs to.
You are given a question and a shortlist of candidate topics (already ranked by embedding
similarity). Return ONLY JSON: {"topic_id": "<best matching id from the shortlist>"}.
If none of the candidates fit, return {"topic_id": null}."""

# Matches the start of a numbered exam question: "Q1.", "Q 1)", "1.", "12)".
QUESTION_START = re.compile(r"(?:^|\n)\s*(?:Q\s*)?(\d{1,2})\s*[.)]\s+", re.IGNORECASE)

MIN_QUESTION_CHARS = 15
MAX_QUESTION_CHARS = 1_000


async def extract_topic_tree(syllabus_text: str) -> dict:
    """LLM call -> {"subject": str, "topics": [{"topic": str, "subtopics": [str]}]}.

    The schema guarantees that shape, so callers can index it without guarding.
    """
    return await generate_json(
        TOPIC_TREE_SYSTEM_PROMPT, syllabus_text, schema=TOPIC_TREE_SCHEMA
    )


async def confirm_past_question_topic(
    question_text: str, candidate_topics: list[dict]
) -> str | None:
    """LLM confirms the best topic match from a vector-search shortlist.

    `candidate_topics` is [{"id": str, "name": str}, ...], already narrowed by
    embedding similarity. Returns the chosen topic_id, or None if nothing fits.
    """
    prompt = f"Question: {question_text}\n\nCandidate topics: {candidate_topics}"
    result = await generate_json(
        PAST_QUESTION_TOPIC_SYSTEM_PROMPT, prompt, schema=PAST_QUESTION_TOPIC_SCHEMA
    )
    return result["topic_id"] or None


def split_past_paper(text: str) -> list[str]:
    """Split a past paper into individual questions on "Q1"/"1." style markers.

    Regex rather than an LLM call because papers are numbered predictably and
    this runs over every past paper the student uploads. Fragments that are too
    short to be a real question are dropped.
    """
    matches = list(QUESTION_START.finditer(text))
    if not matches:
        return []

    questions: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = " ".join(text[start:end].split())
        if MIN_QUESTION_CHARS <= len(body):
            questions.append(body[:MAX_QUESTION_CHARS])
    return questions


def extract_year(filename: str) -> int | None:
    """Pull a 4-digit exam year out of a past-paper filename, if present."""
    match = re.search(r"(19|20)\d{2}", filename)
    return int(match.group(0)) if match else None
