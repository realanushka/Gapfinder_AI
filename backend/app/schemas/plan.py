import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.topic_score import MasteryStatus


class PlanGenerationRequest(BaseModel):
    days: int
    hours_per_day: float


class PlanTask(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    minutes: int
    description: str
    citation: str | None = None


class PlanDay(BaseModel):
    day: int
    tasks: list[PlanTask]


class PlanChange(BaseModel):
    """A topic whose mastery band moved between the last two quiz attempts."""

    topic_id: uuid.UUID
    topic_name: str
    from_status: MasteryStatus
    to_status: MasteryStatus
    improved: bool


class PlanResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    days: list[PlanDay]
    changes: list[PlanChange] = []
