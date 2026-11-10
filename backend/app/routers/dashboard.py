from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.topic import Topic
from app.models.topic_score import MasteryStatus, TopicScore
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, TopicProgress, TopicProgressPoint

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    topics = (await db.scalars(select(Topic).where(Topic.user_id == current_user.id))).all()

    topic_progress: list[TopicProgress] = []
    latest_statuses: dict[str, MasteryStatus] = {}
    earliest_statuses: dict[str, MasteryStatus] = {}

    for topic in topics:
        scores = (
            await db.scalars(
                select(TopicScore)
                .where(TopicScore.topic_id == topic.id, TopicScore.user_id == current_user.id)
                .order_by(TopicScore.attempt_no)
            )
        ).all()

        if not scores:
            continue

        topic_progress.append(
            TopicProgress(
                topic_id=topic.id,
                topic_name=topic.name,
                history=[
                    TopicProgressPoint(attempt_no=s.attempt_no, score=s.score) for s in scores
                ],
            )
        )
        earliest_statuses[str(topic.id)] = scores[0].status
        latest_statuses[str(topic.id)] = scores[-1].status

    weak_to_strong_count = sum(
        1
        for topic_id, latest in latest_statuses.items()
        if earliest_statuses.get(topic_id) == MasteryStatus.WEAK
        and latest == MasteryStatus.STRONG
    )

    readiness_percent = (
        100
        * sum(1 for s in latest_statuses.values() if s == MasteryStatus.STRONG)
        / len(latest_statuses)
        if latest_statuses
        else 0.0
    )

    return DashboardResponse(
        readiness_percent=readiness_percent,
        weak_to_strong_count=weak_to_strong_count,
        topics=topic_progress,
    )
