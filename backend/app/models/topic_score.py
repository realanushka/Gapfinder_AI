import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MasteryStatus(str, enum.Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


class TopicScore(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A snapshot of a user's mastery of a topic after a given quiz attempt."""

    __tablename__ = "topic_scores"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    # See the note on Document.type: store lowercase values, not member names.
    status: Mapped[MasteryStatus] = mapped_column(
        Enum(MasteryStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
