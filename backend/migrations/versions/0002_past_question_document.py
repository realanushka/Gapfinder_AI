"""add document_id to past_questions

A past question needs to know which past-paper document it came from: topic_id
is nullable, so it cannot identify the owning user, and re-running the
past-paper mapping needs a way to clear the rows it previously created.

Revision ID: 0002_past_question_document
Revises: 0001_initial_schema
Create Date: 2026-11-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_past_question_document"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "past_questions",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_past_questions_document_id",
        "past_questions",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Exam weight is computed by counting past questions per topic, so that
    # grouping is the hot path once papers are mapped.
    op.create_index("ix_past_questions_topic_id", "past_questions", ["topic_id"])


def downgrade() -> None:
    op.drop_index("ix_past_questions_topic_id", table_name="past_questions")
    op.drop_constraint("fk_past_questions_document_id", "past_questions", type_="foreignkey")
    op.drop_column("past_questions", "document_id")
