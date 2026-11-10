import uuid

from pydantic import BaseModel


class TopicProgressPoint(BaseModel):
    attempt_no: int
    score: float


class TopicProgress(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    history: list[TopicProgressPoint]


class DashboardResponse(BaseModel):
    readiness_percent: float
    weak_to_strong_count: int
    topics: list[TopicProgress]
