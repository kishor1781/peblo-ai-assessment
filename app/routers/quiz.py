"""
Quiz Router

POST /generate-quiz  – Generate questions from ingested content using LLM.
GET  /quiz           – Retrieve questions with optional filters.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuizQuestion
from app.schemas import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    QuestionOut,
    QuizListResponse,
)
from app.services import quiz as quiz_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Quiz"])


@router.post(
    "/generate-quiz",
    response_model=GenerateQuizResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate quiz questions from a source document",
    description=(
        "Calls the LLM to generate MCQ, True/False, and Fill-in-blank questions "
        "for all content chunks of the specified source document."
    ),
)
def generate_quiz(
    request: GenerateQuizRequest,
    db: Session = Depends(get_db),
):
    try:
        questions = quiz_service.generate_quiz_for_source(
            source_id=request.source_id,
            db=db,
            max_questions_per_chunk=request.max_questions_per_chunk,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Quiz generation failed for source %s", request.source_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quiz generation failed: {exc}",
        )

    return GenerateQuizResponse(
        source_id=request.source_id,
        questions_generated=len(questions),
        message=f"Successfully generated {len(questions)} question(s) for source '{request.source_id}'.",
    )


@router.get(
    "/quiz",
    response_model=QuizListResponse,
    summary="Retrieve quiz questions",
    description=(
        "Fetch quiz questions with optional filters. "
        "All parameters are optional and can be combined."
    ),
)
def get_quiz(
    topic: Optional[str] = Query(None, description="Filter by topic (e.g. 'Shapes', 'Grammar')"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty: easy | medium | hard"),
    grade: Optional[int] = Query(None, description="Filter by grade level (e.g. 1, 3, 4)"),
    subject: Optional[str] = Query(None, description="Filter by subject (e.g. 'Math', 'Science')"),
    question_type: Optional[str] = Query(None, description="Filter by type: MCQ | TrueFalse | FillBlank"),
    source_id: Optional[str] = Query(None, description="Filter by source document ID"),
    limit: int = Query(10, ge=1, le=100, description="Max questions to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    query = db.query(QuizQuestion)

    if topic:
        query = query.filter(QuizQuestion.topic.ilike(f"%{topic}%"))
    if difficulty:
        query = query.filter(QuizQuestion.difficulty == difficulty.lower())
    if grade:
        query = query.filter(QuizQuestion.grade == grade)
    if subject:
        query = query.filter(QuizQuestion.subject.ilike(f"%{subject}%"))
    if question_type:
        query = query.filter(QuizQuestion.question_type == question_type)
    if source_id:
        from app.models import ContentChunk
        chunk_ids = [c.chunk_id for c in db.query(ContentChunk.chunk_id).filter_by(source_id=source_id)]
        query = query.filter(QuizQuestion.chunk_id.in_(chunk_ids))

    total = query.count()
    questions = query.offset(offset).limit(limit).all()

    return QuizListResponse(
        total=total,
        questions=[_to_question_out(q) for q in questions],
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _to_question_out(q: QuizQuestion) -> QuestionOut:
    options = None
    if q.options_json:
        try:
            options = json.loads(q.options_json)
        except Exception:
            options = None

    return QuestionOut(
        question_id=q.question_id,
        chunk_id=q.chunk_id,
        question=q.question,
        question_type=q.question_type,
        options=options,
        answer=q.answer,
        difficulty=q.difficulty,
        topic=q.topic,
        grade=q.grade,
        subject=q.subject,
    )
