import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.document import Document, DocumentType
from app.models.topic import Topic
from app.models.user import User
from app.schemas.syllabus import SyllabusDetail, SyllabusSummary
from app.services.topic_map_service import build_tree

router = APIRouter(prefix="/syllabi", tags=["syllabi"])


@router.get("", response_model=list[SyllabusSummary])
async def list_syllabi(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SyllabusSummary]:
    """Syllabi whose topic map has been saved -- these become sidebar shortcuts."""
    rows = (
        await db.execute(
            select(Document, func.count(Topic.id))
            .outerjoin(Topic, Topic.document_id == Document.id)
            .where(
                Document.user_id == current_user.id,
                Document.type == DocumentType.SYLLABUS,
                Document.subject.is_not(None),
            )
            .group_by(Document.id)
            .order_by(Document.subject)
        )
    ).all()
    return [
        SyllabusSummary(
            document_id=document.id,
            subject=document.subject or "",
            filename=document.filename,
            topic_count=count,
        )
        for document, count in rows
    ]


@router.get("/{document_id}", response_model=SyllabusDetail)
async def get_syllabus(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyllabusDetail:
    document = await db.get(Document, document_id)
    if (
        document is None
        or document.user_id != current_user.id
        or document.type != DocumentType.SYLLABUS
        or document.subject is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Syllabus not found")

    topics = list(
        (
            await db.scalars(
                select(Topic).where(
                    Topic.user_id == current_user.id, Topic.document_id == document.id
                )
            )
        ).all()
    )
    return SyllabusDetail(
        document_id=document.id,
        subject=document.subject,
        filename=document.filename,
        created_at=document.created_at,
        topic_count=len(topics),
        topics=build_tree(topics),
    )
