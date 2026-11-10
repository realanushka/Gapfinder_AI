import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.chunk import Chunk
from app.models.chunk_topic import ChunkTopic
from app.models.plan import Plan
from app.models.topic_score import TopicScore
from app.models.user import User
from app.schemas.plan import (
    PlanChange,
    PlanDay,
    PlanGenerationRequest,
    PlanResponse,
    PlanTask,
)
from app.services.gap_report_service import diagnose_topics
from app.services.planning_service import build_schedule, compute_priority, describe_task

router = APIRouter(prefix="/plan", tags=["plan"])


async def _source_reference(
    db: AsyncSession, topic_id: uuid.UUID
) -> tuple[str | None, str | None, int | None]:
    """A chapter/section/page for this topic, so each task points at real pages."""
    chunk = await db.scalar(
        select(Chunk)
        .join(ChunkTopic, ChunkTopic.chunk_id == Chunk.id)
        .where(ChunkTopic.topic_id == topic_id)
        .order_by(Chunk.page)
        .limit(1)
    )
    if chunk is None:
        return None, None, None
    return chunk.chapter, chunk.section, chunk.page


async def _status_changes(db: AsyncSession, user_id: uuid.UUID) -> list[PlanChange]:
    """Compare each topic's two most recent snapshots to show what moved.

    This is what makes the plan visibly "update" after a retake (Step 8.5):
    "Algebra moved from Weak to Medium".
    """
    rows = list(
        (
            await db.scalars(
                select(TopicScore)
                .where(TopicScore.user_id == user_id)
                .order_by(TopicScore.topic_id, TopicScore.attempt_no)
            )
        ).all()
    )

    by_topic: dict[uuid.UUID, list[TopicScore]] = {}
    for row in rows:
        by_topic.setdefault(row.topic_id, []).append(row)

    diagnoses = {d.topic_id: d.topic_name for d in await diagnose_topics(db, user_id, False)}

    changes: list[PlanChange] = []
    for topic_id, history in by_topic.items():
        if len(history) < 2:
            continue
        previous, latest = history[-2], history[-1]
        if previous.status != latest.status:
            changes.append(
                PlanChange(
                    topic_id=topic_id,
                    topic_name=diagnoses.get(topic_id, "Topic"),
                    from_status=previous.status,
                    to_status=latest.status,
                    improved=latest.score > previous.score,
                )
            )
    return changes


@router.post("/generate", response_model=PlanResponse)
async def generate_plan(
    payload: PlanGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    diagnoses = await diagnose_topics(db, current_user.id, with_reasons=False)

    topics_input = [
        {
            "topic_id": diagnosis.topic_id,
            "topic_name": diagnosis.topic_name,
            "status": diagnosis.status.value,
            # Pure arithmetic, so the ordering is explainable without the LLM.
            "priority": compute_priority(diagnosis.score, diagnosis.exam_weight),
        }
        for diagnosis in diagnoses
    ]

    schedule = build_schedule(topics_input, payload.days, payload.hours_per_day)

    days: list[PlanDay] = []
    for day_index, day_topics in enumerate(schedule, start=1):
        tasks: list[PlanTask] = []
        for topic in day_topics:
            chapter, section, page = await _source_reference(db, topic["topic_id"])
            description = await describe_task(topic["topic_name"], chapter, section, page)
            tasks.append(
                PlanTask(
                    topic_id=topic["topic_id"],
                    topic_name=topic["topic_name"],
                    minutes=topic["minutes"],
                    description=description.strip(),
                    citation=", ".join(
                        part
                        for part in (chapter, section, f"p. {page}" if page else None)
                        if part
                    )
                    or None,
                )
            )
        days.append(PlanDay(day=day_index, tasks=tasks))

    changes = await _status_changes(db, current_user.id)

    plan_json = {
        "days": [day.model_dump(mode="json") for day in days],
        "changes": [change.model_dump(mode="json") for change in changes],
    }
    plan = Plan(user_id=current_user.id, plan_json=plan_json)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return PlanResponse(id=plan.id, created_at=plan.created_at, days=days, changes=changes)


@router.get("/latest", response_model=PlanResponse | None)
async def get_latest_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse | None:
    plan = await db.scalar(
        select(Plan).where(Plan.user_id == current_user.id).order_by(Plan.created_at.desc())
    )
    if plan is None:
        return None

    return PlanResponse(
        id=plan.id,
        created_at=plan.created_at,
        days=[PlanDay(**day) for day in plan.plan_json.get("days", [])],
        changes=[PlanChange(**change) for change in plan.plan_json.get("changes", [])],
    )
