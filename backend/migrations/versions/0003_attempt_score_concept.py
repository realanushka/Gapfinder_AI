"""add score and concept_tag to attempts

Short-answer grading already produces a partial score and the concept that was
missed, but neither was stored: topic scores could only count right/wrong, and
the gap report's diagnosis had no concepts to name.

Revision ID: 0003_attempt_score_concept
Revises: 0002_past_question_document
Create Date: 2026-11-10

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003_attempt_score_concept"
down_revision: Union[str, None] = "0002_past_question_document"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default backfills existing rows; the model keeps a client-side
    # default so new inserts stay explicit.
    op.add_column(
        "attempts",
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column("attempts", sa.Column("concept_tag", sa.String(length=255), nullable=True))

    # Topic scoring reads a user's attempts for one topic at a time.
    op.create_index("ix_attempts_user_question", "attempts", ["user_id", "question_id"])


def downgrade() -> None:
    op.drop_index("ix_attempts_user_question", table_name="attempts")
    op.drop_column("attempts", "concept_tag")
    op.drop_column("attempts", "score")
