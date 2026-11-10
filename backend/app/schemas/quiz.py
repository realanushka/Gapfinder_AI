import uuid

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    question: str
    options: dict | None
    source_chunk_id: uuid.UUID
    citation: str | None = None

    class Config:
        from_attributes = True


class QuizGenerationRequest(BaseModel):
    """Omit topic_id for a retake weighted toward the student's weakest topics.

    Omit num_questions to let the count scale with each topic's exam weight.
    """

    topic_id: uuid.UUID | None = None
    num_questions: int | None = None
