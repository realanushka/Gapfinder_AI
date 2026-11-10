import uuid

from pydantic import BaseModel


class AnswerSubmission(BaseModel):
    question_id: uuid.UUID
    student_answer: str


class AnswerResult(BaseModel):
    question_id: uuid.UUID
    is_correct: bool | None
    score: float
    feedback: str
    concept_tag: str | None = None
