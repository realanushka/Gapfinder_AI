import uuid

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class PastQuestion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "past_questions"

    text: Mapped[str] = mapped_column(Text, nullable=False)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Which past-paper document this question was extracted from. Without it a
    # question can't be scoped to a user (topic_id is nullable, so it is not a
    # reliable owner) and re-running the mapping couldn't clear its own old rows.
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )

    # Exam weight counts past questions per topic, so that grouping is the hot
    # path. Declared here as well as in the migration, otherwise a later
    # autogenerate run would see an unknown index and drop it.
    __table_args__ = (Index("ix_past_questions_topic_id", "topic_id"),)
