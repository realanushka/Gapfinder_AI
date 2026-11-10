from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.attempt import Attempt
from app.models.chunk import Chunk
from app.models.question import Question
from app.models.user import User
from app.schemas.evaluate import AnswerResult, AnswerSubmission
from app.services.evaluation_service import grade_mcq, grade_short_answer

router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.post("/answer", response_model=AnswerResult)
async def submit_answer(
    payload: AnswerSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnswerResult:
    question = await db.get(Question, payload.question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")

    if question.options:
        is_correct = grade_mcq(payload.student_answer, question.correct_answer)
        score = 1.0 if is_correct else 0.0
        feedback = question.explanation or ""
        concept_tag = None
    else:
        source_chunk = await db.get(Chunk, question.source_chunk_id)
        verdict = await grade_short_answer(
            question.question, payload.student_answer, source_chunk.text if source_chunk else ""
        )
        is_correct = verdict["verdict"] == "correct"
        score = verdict["score"]
        feedback = verdict["reason"]
        concept_tag = verdict.get("concept_tag")

    db.add(
        Attempt(
            user_id=current_user.id,
            question_id=question.id,
            student_answer=payload.student_answer,
            is_correct=is_correct,
            feedback=feedback,
            score=score,
            concept_tag=concept_tag,
        )
    )
    await db.commit()

    return AnswerResult(
        question_id=question.id,
        is_correct=is_correct,
        score=score,
        feedback=feedback,
        concept_tag=concept_tag,
    )
