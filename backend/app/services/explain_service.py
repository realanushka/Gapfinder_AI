"""Retrieval-grounded "Explain this topic" assistant (Plan Step 9)."""

from app.services.llm_client import generate_text

EXPLAIN_SYSTEM_PROMPT = """Answer ONLY using the context below. Cite the sources by
chapter/section/page. If the answer is not in the context, say exactly:
"This isn't covered in your uploaded material." Never use outside knowledge."""

CURRICULUM_PROMPT = """

You are tutoring a student on the syllabus outlined here. Use the outline ONLY to
understand where the question sits in their curriculum -- you may mention which topic
it belongs to, and keep the answer pitched at that level. It is NOT a source of facts:
every fact in your answer must still come from the context passages.

SYLLABUS OUTLINE:
"""


async def answer_from_context(
    question: str, context_chunks: list[dict], curriculum: str = ""
) -> str:
    """context_chunks: [{"text", "chapter", "section", "page"}, ...], the top
    4-6 chunks retrieved for the student's question (Step 9.2).

    `curriculum` is the saved syllabus outline (see topic_map_service); when
    present it is embedded in the system prompt as the foundation for the answer.
    """
    context_text = "\n\n".join(
        f"[{c.get('chapter')} {c.get('section')} p.{c.get('page')}] {c['text']}"
        for c in context_chunks
    )
    system_prompt = EXPLAIN_SYSTEM_PROMPT
    if curriculum:
        system_prompt += CURRICULUM_PROMPT + curriculum

    prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
    return await generate_text(system_prompt, prompt)
