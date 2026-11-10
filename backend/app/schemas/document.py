import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.document import DocumentType

MAX_FILENAME_CHARS = 255


class DocumentResponse(BaseModel):
    id: uuid.UUID
    type: DocumentType
    filename: str
    created_at: datetime
    # Searchable chunks the file was split into (0 until ingestion finishes).
    chunk_count: int = 0
    # Set once the syllabus's topic map has been saved (syllabus files only).
    subject: str | None = None

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    chunks_created: int


class DocumentDetails(DocumentResponse):
    """What the "View details" action shows for one file."""

    page_count: int
    topic_count: int


class DocumentRename(BaseModel):
    filename: str

    @field_validator("filename")
    @classmethod
    def _clean(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("The file name cannot be empty.")
        if len(value) > MAX_FILENAME_CHARS:
            raise ValueError(f"The file name must be at most {MAX_FILENAME_CHARS} characters.")
        if "/" in value or "\\" in value:
            raise ValueError("The file name cannot contain slashes.")
        return value


class DocumentContent(BaseModel):
    """The extracted text of a file, so it can be previewed before a topic build."""

    filename: str
    text: str
    truncated: bool
