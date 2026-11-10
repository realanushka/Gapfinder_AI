import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Topic(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "topics"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=True
    )
    exam_weight: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # The syllabus this topic came from. Lets several syllabi (Physics,
    # Chemistry, ...) coexist, and deleting a syllabus removes its topic map.
    # NULL for topics that predate this column.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )

    __table_args__ = (Index("ix_topics_document_id", "document_id"),)
