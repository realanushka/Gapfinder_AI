import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.topic_score import TopicScore
from app.models.user import User
from app.schemas.gap_report import TopicGapCard
from app.services.gap_report_service import TopicDiagnosis, diagnose_topics

router = APIRouter(prefix="/gap-report", tags=["gap-report"])


def to_card(diagnosis: TopicDiagnosis) -> TopicGapCard:
    return TopicGapCard(
        topic_id=diagnosis.topic_id,
        topic_name=diagnosis.topic_name,
        score=diagnosis.score,
        status=diagnosis.status,
        reason=diagnosis.reason,
        exam_weight=diagnosis.exam_weight,
    )


@router.get("", response_model=list[TopicGapCard])
async def get_gap_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TopicGapCard]:
    diagnoses = await diagnose_topics(db, current_user.id)
    return [to_card(diagnosis) for diagnosis in diagnoses]


@router.post("/snapshot", response_model=list[TopicGapCard])
async def snapshot_gap_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TopicGapCard]:
    """Record the current scores as a numbered attempt.

    Called once a quiz is finished. `GET /gap-report` stays a pure read, so this
    is the only place that writes history -- which is what the progress
    dashboard charts.
    """
    diagnoses = await diagnose_topics(db, current_user.id)

    # Attempt numbers advance per topic, since topics can be quizzed separately.
    existing = dict(
        (
            await db.execute(
                select(TopicScore.topic_id, func.max(TopicScore.attempt_no))
                .where(TopicScore.user_id == current_user.id)
                .group_by(TopicScore.topic_id)
            )
        ).all()
    )

    for diagnosis in diagnoses:
        last: int | None = existing.get(diagnosis.topic_id)
        db.add(
            TopicScore(
                user_id=current_user.id,
                topic_id=diagnosis.topic_id,
                attempt_no=(last or 0) + 1,
                score=diagnosis.score,
                status=diagnosis.status,
                reason=diagnosis.reason,
            )
        )

    await db.commit()
    return [to_card(diagnosis) for diagnosis in diagnoses]
