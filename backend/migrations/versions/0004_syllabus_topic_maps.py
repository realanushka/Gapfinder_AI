"""link topics to their syllabus and name saved topic maps

Several syllabi (Physics, Chemistry, ...) must be able to coexist, each with
its own saved topic map shown as a sidebar shortcut:

* topics.document_id -- which syllabus a topic came from. ON DELETE CASCADE, so
  deleting a syllabus file removes its topic map.
* documents.subject -- the name shown in the sidebar. Non-null means the
  syllabus's topic map has been saved.

Revision ID: 0004_syllabus_topic_maps
Revises: 0003_attempt_score_concept
Create Date: 2026-11-10

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004_syllabus_topic_maps"
down_revision: Union[str, None] = "0003_attempt_score_concept"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("subject", sa.String(length=255), nullable=True))
    op.add_column("topics", sa.Column("document_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_topics_document_id_documents",
        "topics",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_topics_document_id", "topics", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_topics_document_id", table_name="topics")
    op.drop_constraint("fk_topics_document_id_documents", "topics", type_="foreignkey")
    op.drop_column("topics", "document_id")
    op.drop_column("documents", "subject")
