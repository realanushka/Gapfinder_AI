from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.topic import Topic
from app.schemas.explain import Citation, ExplainRequest, ExplainResponse
from app.services.embedding_client import embed_text
from app.services.explain_service import answer_from_context
from app.services.retrieval_service import search_chunks, search_chunks_for_topic
from app.services.topic_map_service import curriculum_context

router = APIRouter(prefix="/explain", tags=["explain"])

TOP_K_CHUNKS = 6
NOT_COVERED_MESSAGE = "This isn't covered in your uploaded material."


@router.post("", response_model=ExplainResponse)
async def explain(
    payload: ExplainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExplainResponse:
    topic: Topic | None = None
    if payload.topic_id is not None:
        topic = await db.get(Topic, payload.topic_id)
        if topic is None or topic.user_id != current_user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Topic not found")

    query_embedding = await embed_text(payload.question)

    # "Focus on a topic" narrows retrieval to the material linked to that topic.
    # If nothing is linked (e.g. no notes covered it), fall back to everything
    # rather than answering "not covered" from an empty search.
    rows = []
    if topic is not None:
        rows = await search_chunks_for_topic(
            db, current_user.id, topic.id, query_embedding, limit=TOP_K_CHUNKS
        )
    if not rows:
        rows = await search_chunks(db, current_user.id, query_embedding, limit=TOP_K_CHUNKS)

    curriculum = await curriculum_context(db, current_user.id, topic)

    context = [
        {"text": c.text, "chapter": c.chapter, "section": c.section, "page": c.page}
        for c in rows
    ]

    answer = await answer_from_context(payload.question, context, curriculum)
    covered = NOT_COVERED_MESSAGE not in answer

    citations = (
        [Citation(chunk_id=c.id, chapter=c.chapter, section=c.section, page=c.page) for c in rows]
        if covered
        else []
    )

    return ExplainResponse(answer=answer, citations=citations, covered_by_material=covered)
