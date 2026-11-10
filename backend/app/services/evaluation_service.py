"""Grade answers and explain them (Plan Step 6)."""

from app.services.llm_client import generate_json
from app.services.schemas import SHORT_ANSWER_GRADE_SCHEMA

SHORT_ANSWER_GRADING_SYSTEM_PROMPT = """You grade a student's short answer against the source
material. Judge only against the source material, never outside knowledge.
"score" is between 0.0 and 1.0. "concept_tag" names the specific concept inside the topic
that was missed (e.g. "light reaction"), or null if the answer was correct."""


def grade_mcq(student_answer: str, correct_answer: str) -> bool:
    """MCQs are graded directly, no LLM needed (Step 6.1)."""
    return student_answer.strip().upper() == correct_answer.strip().upper()


async def grade_short_answer(question: str, student_answer: str, source_chunk_text: str) -> dict:
    """Grade one short answer -> {verdict, score, reason, concept_tag}.

    The schema guarantees the shape and that `verdict` is one of the three
    allowed values. It cannot express numeric bounds, so `score` is clamped
    here -- a score outside 0..1 would otherwise skew the topic average and
    push a mastery band the wrong way.
    """
    prompt = (
        f"Question: {question}\n\n"
        f"Student answer: {student_answer}\n\n"
        f"Source material: {source_chunk_text}"
    )
    result = await generate_json(
        SHORT_ANSWER_GRADING_SYSTEM_PROMPT, prompt, schema=SHORT_ANSWER_GRADE_SCHEMA
    )

    result["score"] = max(0.0, min(1.0, float(result["score"])))
    return result
