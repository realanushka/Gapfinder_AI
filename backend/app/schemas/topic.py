import uuid

from pydantic import BaseModel, field_validator

MAX_NAME_CHARS = 255


class TopicResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    exam_weight: int
    # The syllabus this topic belongs to (None for topics that predate syllabi).
    document_id: uuid.UUID | None = None

    class Config:
        from_attributes = True


class TopicTreeNode(BaseModel):
    id: uuid.UUID
    name: str
    exam_weight: int
    subtopics: list["TopicTreeNode"] = []


TopicTreeNode.model_rebuild()


class TopicBuildResult(BaseModel):
    """Outcome of saving a topic map, so the UI can report what actually happened."""

    document_id: uuid.UUID
    subject: str
    topics: list[TopicTreeNode]
    topics_created: int
    chunks_linked: int
    past_questions_mapped: int


class TopicDraft(BaseModel):
    """One topic and its subtopic names, before anything is saved."""

    name: str
    subtopics: list[str] = []

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return " ".join(value.split())[:MAX_NAME_CHARS]

    @field_validator("subtopics")
    @classmethod
    def _subtopics(cls, value: list[str]) -> list[str]:
        return [" ".join(item.split())[:MAX_NAME_CHARS] for item in value]


class TopicPreview(BaseModel):
    """Result of "Topic Build": the extracted structure, not yet persisted."""

    document_id: uuid.UUID
    subject: str
    topics: list[TopicDraft]


class TopicMapSave(BaseModel):
    document_id: uuid.UUID
    subject: str
    topics: list[TopicDraft]

    @field_validator("subject")
    @classmethod
    def _subject(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Give the subject a name.")
        return value[:MAX_NAME_CHARS]
