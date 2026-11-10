import uuid

from pydantic import BaseModel


class ExplainRequest(BaseModel):
    question: str
    topic_id: uuid.UUID | None = None


class Citation(BaseModel):
    chunk_id: uuid.UUID
    chapter: str | None
    section: str | None
    page: int | None


class ExplainResponse(BaseModel):
    answer: str
    citations: list[Citation]
    covered_by_material: bool
