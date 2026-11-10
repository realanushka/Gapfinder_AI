"""Vector similarity search over a user's own material.

This is the "R" in RAG and the single place retrieval happens, so every feature
(topic linking, quiz generation, the explain assistant) is guaranteed to be
scoped to the requesting user's documents and to rank the same way the HNSW
index is built for (cosine distance).
"""

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.chunk_topic import ChunkTopic
from app.models.document import Document, DocumentType

# Topic linking and quiz generation read from study material, never from the
# syllabus (which is only an outline) or past papers (questions, not content).
STUDY_MATERIAL_TYPES = (DocumentType.NOTES, DocumentType.TEXTBOOK)


def _base_query(user_id: uuid.UUID, doc_types: tuple[DocumentType, ...] | None) -> Select:
    query = (
        select(Chunk)
        .join(Document, Document.id == Chunk.document_id)
        .where(Document.user_id == user_id, Chunk.embedding.is_not(None))
    )
    if doc_types:
        query = query.where(Document.type.in_(doc_types))
    return query


async def search_chunks(
    db: AsyncSession,
    user_id: uuid.UUID,
    embedding: list[float],
    limit: int = 6,
    doc_types: tuple[DocumentType, ...] | None = None,
) -> list[Chunk]:
    """Return the `limit` chunks closest to `embedding`, nearest first."""
    query = (
        _base_query(user_id, doc_types)
        .order_by(Chunk.embedding.cosine_distance(embedding))
        .limit(limit)
    )
    return list((await db.scalars(query)).all())


async def search_chunks_for_topic(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic_id: uuid.UUID,
    embedding: list[float],
    limit: int = 6,
) -> list[Chunk]:
    """Nearest chunks among those linked to one topic (the "focus on a topic" case)."""
    query = (
        _base_query(user_id, STUDY_MATERIAL_TYPES)
        .join(ChunkTopic, ChunkTopic.chunk_id == Chunk.id)
        .where(ChunkTopic.topic_id == topic_id)
        .order_by(Chunk.embedding.cosine_distance(embedding))
        .limit(limit)
    )
    return list((await db.scalars(query)).all())


async def search_chunks_scored(
    db: AsyncSession,
    user_id: uuid.UUID,
    embedding: list[float],
    limit: int = 6,
    doc_types: tuple[DocumentType, ...] | None = None,
) -> list[tuple[Chunk, float]]:
    """Like `search_chunks`, but also returns cosine similarity (1.0 = identical)."""
    distance = Chunk.embedding.cosine_distance(embedding)
    query = _base_query(user_id, doc_types).add_columns(distance).order_by(distance).limit(limit)
    return [(chunk, 1.0 - float(dist)) for chunk, dist in (await db.execute(query)).all()]


async def document_text(db: AsyncSession, document_id: uuid.UUID, max_chars: int = 24_000) -> str:
    """Reassemble a document's text from its chunks, in reading order.

    Truncated because this feeds an LLM prompt (syllabus extraction, past-paper
    splitting) and a long textbook would otherwise blow the context window.
    """
    chunks = list(
        (
            await db.scalars(
                select(Chunk)
                .where(Chunk.document_id == document_id)
                .order_by(Chunk.page, Chunk.id)
            )
        ).all()
    )

    text = "\n".join(chunk.text for chunk in chunks)
    return text[:max_chars]
