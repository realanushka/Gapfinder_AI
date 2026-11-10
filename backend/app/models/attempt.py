import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Attempt(UUIDPrimaryKeyMixin, Base):
    """A student's answer to a single question (MCQ or short-answer)."""

    __tablename__ = "attempts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    student_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Partial credit from short-answer grading; 1.0/0.0 for an MCQ. Topic scores
    # average this, so a half-right long answer isn't counted as fully wrong.
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Which concept inside the topic was missed ("light reaction"). Persisted so
    # the gap report's diagnosis can name it instead of being generic.
    concept_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Declared here as well as in migration 0003 so autogenerate doesn't drop it.
    __table_args__ = (Index("ix_attempts_user_question", "user_id", "question_id"),)
