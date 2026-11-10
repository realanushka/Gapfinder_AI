import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentType(str, enum.Enum):
    SYLLABUS = "syllabus"
    NOTES = "notes"
    TEXTBOOK = "textbook"
    PAST_PAPER = "past_paper"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # values_callable stores the lowercase member values ("syllabus", ...) rather
    # than SQLAlchemy's default of member NAMES ("SYLLABUS"), keeping the Postgres
    # labels identical to the API representation and to ARCHITECTURE.md.
    type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)

    # Set when a syllabus's topic map is saved. It is the name shown in the
    # sidebar ("Physics Syllabus"), so a non-null value also means "saved".
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
