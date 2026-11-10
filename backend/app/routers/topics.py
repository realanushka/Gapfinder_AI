import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.document import Document, DocumentType
from app.models.topic import Topic
from app.models.user import User
from app.schemas.topic import (
    TopicBuildResult,
    TopicDraft,
    TopicMapSave,
    TopicPreview,
    TopicResponse,
)
from app.services.retrieval_service import document_text
from app.services.topic_map_service import clean_draft, save_topic_map
from app.services.topic_service import extract_topic_tree

router = APIRouter(prefix="/topics", tags=["topics"])


async def _owned_syllabus(db: AsyncSession, user: User, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if document.type != DocumentType.SYLLABUS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Topic maps are built from a syllabus document",
        )
    return document


def _subject_from_filename(filename: str) -> str:
    """Fallback subject name: 'class10_physics_syllabus.pdf' -> 'Class10 Physics'."""
    stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", filename)
    words = re.sub(r"[_\-]+", " ", stem).split()
    words = [w for w in words if w.lower() != "syllabus"]
    return " ".join(words).title() or "Syllabus"


async def _extract_drafts(db: AsyncSession, document: Document) -> tuple[str, list[TopicDraft]]:
    """Run the topic-extraction LLM call. Persists nothing."""
    syllabus_text = await document_text(db, document.id)
    if not syllabus_text.strip():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That syllabus has no extracted text — re-upload it as a text-based PDF",
        )

    extracted = await extract_topic_tree(syllabus_text)

    drafts = clean_draft(
        [
            TopicDraft(
                name=str(entry.get("topic") or ""),
                subtopics=[str(sub or "") for sub in entry.get("subtopics", [])],
            )
            for entry in extracted.get("topics", [])
        ]
    )
    if not drafts:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No topics could be extracted from that syllabus",
        )

    subject = " ".join(str(extracted.get("subject") or "").split())
    return subject or _subject_from_filename(document.filename), drafts


@router.post("/preview/{document_id}", response_model=TopicPreview)
async def preview_topic_map(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicPreview:
    """"Topic Build": extract the structure from a syllabus and show it for review.

    One LLM call and nothing is written, so the student can inspect (and trim)
    the result before it is saved.
    """
    document = await _owned_syllabus(db, current_user, document_id)
    subject, drafts = await _extract_drafts(db, document)
    return TopicPreview(document_id=document.id, subject=subject, topics=drafts)


@router.post("/save", response_model=TopicBuildResult)
async def save_reviewed_topic_map(
    payload: TopicMapSave,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicBuildResult:
    """Persist the reviewed map, then link study material and weight by past papers.

    Saving is what makes the syllabus appear as a sidebar shortcut.
    """
    document = await _owned_syllabus(db, current_user, payload.document_id)
    if not clean_draft(payload.topics):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "There are no topics to save."
        )

    result = await save_topic_map(db, current_user.id, document, payload.subject, payload.topics)
    await db.commit()
    return result


@router.post("/build-from-syllabus/{document_id}", response_model=TopicBuildResult)
async def build_topic_map(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopicBuildResult:
    """One-shot build + save, for API clients that do not need the review step."""
    document = await _owned_syllabus(db, current_user, document_id)
    subject, drafts = await _extract_drafts(db, document)
    result = await save_topic_map(db, current_user.id, document, subject, drafts)
    await db.commit()
    return result


@router.get("", response_model=list[TopicResponse])
async def list_topics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Topic]:
    result = await db.scalars(
        select(Topic).where(Topic.user_id == current_user.id).order_by(Topic.name)
    )
    return list(result.all())
