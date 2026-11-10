import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.topic import TopicTreeNode


class SyllabusSummary(BaseModel):
    """One sidebar shortcut: a syllabus whose topic map has been saved."""

    document_id: uuid.UUID
    subject: str
    filename: str
    topic_count: int


class SyllabusDetail(BaseModel):
    document_id: uuid.UUID
    subject: str
    filename: str
    created_at: datetime
    topic_count: int
    topics: list[TopicTreeNode]
