import uuid

from pydantic import BaseModel

from app.models.topic_score import MasteryStatus


class TopicGapCard(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    score: float
    status: MasteryStatus
    reason: str
    exam_weight: int
