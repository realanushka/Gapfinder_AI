import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.chunk import Chunk
from app.models.document import Document, DocumentType
from app.models.topic import Topic
from app.models.user import User
from app.schemas.document import (
    DocumentContent,
    DocumentDetails,
    DocumentRename,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.embedding_client import embed_texts
from app.services.ingestion_service import chunk_text, detect_structure, extract_pages
from app.services.retrieval_service import document_text
from app.services.topic_map_service import recompute_exam_weights

router = APIRouter(prefix="/documents", tags=["documents"])

# How much of a file the "open its content" preview returns.
PREVIEW_MAX_CHARS = 30_000


async def _owned_document(db: AsyncSession, user: User, document_id: uuid.UUID) -> Document:
    """Fetch a document, treating someone else's like a missing one."""
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


def _response(document: Document, chunk_count: int) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        type=document.type,
        filename=document.filename,
        created_at=document.created_at,
        chunk_count=chunk_count,
        subject=document.subject,
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Save a file into the folder matching `doc_type` (syllabus, notes, ...)."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # Read the file before touching the database, so a bad upload leaves no trace.
    try:
        pages = extract_pages(file_bytes, file.filename or "")
    except Exception as err:  # parser errors vary by backend (PyMuPDF / pdfminer)
        raise HTTPException(
            status_code=400,
            detail="Could not read this file. Please upload a valid, unencrypted PDF or a plain .txt file.",
        ) from err

    chunks = chunk_text(detect_structure(pages))
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No readable text found in this file. Scanned or image-only PDFs are not supported.",
        )

    document = Document(user_id=current_user.id, type=doc_type, filename=file.filename)
    db.add(document)
    await db.flush()

    embeddings = await embed_texts([c.text for c in chunks])

    for draft, embedding in zip(chunks, embeddings, strict=True):
        db.add(
            Chunk(
                document_id=document.id,
                text=draft.text,
                chapter=draft.chapter,
                section=draft.section,
                page=draft.page,
                embedding=embedding,
            )
        )

    await db.commit()
    await db.refresh(document)

    return DocumentUploadResponse(
        document=_response(document, len(chunks)),
        chunks_created=len(chunks),
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """Every uploaded file with its chunk count. The Upload page groups these into
    folders by type; the Topic Map picks a syllabus from them."""
    rows = (
        await db.execute(
            select(Document, func.count(Chunk.id))
            .outerjoin(Chunk, Chunk.document_id == Document.id)
            .where(Document.user_id == current_user.id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
        )
    ).all()
    return [_response(document, count) for document, count in rows]


@router.get("/{document_id}", response_model=DocumentDetails)
async def document_details(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentDetails:
    """"View details" for one file."""
    document = await _owned_document(db, current_user, document_id)

    chunk_count, page_count = (
        await db.execute(
            select(func.count(Chunk.id), func.coalesce(func.max(Chunk.page), 0)).where(
                Chunk.document_id == document.id
            )
        )
    ).one()
    topic_count = await db.scalar(
        select(func.count(Topic.id)).where(Topic.document_id == document.id)
    )

    return DocumentDetails(
        **_response(document, chunk_count).model_dump(),
        page_count=page_count,
        topic_count=topic_count or 0,
    )


@router.get("/{document_id}/content", response_model=DocumentContent)
async def document_content(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentContent:
    """The extracted text of a file, for previewing it before building a topic map."""
    document = await _owned_document(db, current_user, document_id)
    # Ask for one extra character so we can tell "exactly full" from "cut off".
    text = await document_text(db, document.id, max_chars=PREVIEW_MAX_CHARS + 1)
    return DocumentContent(
        filename=document.filename,
        text=text[:PREVIEW_MAX_CHARS],
        truncated=len(text) > PREVIEW_MAX_CHARS,
    )


@router.patch("/{document_id}", response_model=DocumentResponse)
async def rename_document(
    document_id: uuid.UUID,
    payload: DocumentRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Rename a file. Only the display name changes; chunks and topics are untouched."""
    document = await _owned_document(db, current_user, document_id)
    document.filename = payload.filename
    await db.commit()

    chunk_count = await db.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == document.id)
    )
    return _response(document, chunk_count or 0)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a file and everything built from it.

    The database cascades: its chunks go, and with them the quiz questions drawn
    from those chunks. Deleting a syllabus also removes its topic map. A deleted
    past paper stops counting toward exam weights, so those are recomputed.
    """
    document = await _owned_document(db, current_user, document_id)
    was_past_paper = document.type == DocumentType.PAST_PAPER

    await db.delete(document)
    await db.flush()
    if was_past_paper:
        await recompute_exam_weights(db, current_user.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
