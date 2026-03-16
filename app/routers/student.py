"""
Student Router

POST /submit-answer              – Submit a student's answer; returns correctness + adaptive difficulty.
GET  /student-performance/{id}   – Get a student's performance stats and difficulty level.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuizQuestion, StudentAnswer
from app.schemas import (
    StudentPerformance,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services import adaptive as adaptive_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Student"])


@router.post(
    "/submit-answer",
    response_model=SubmitAnswerResponse,
    summary="Submit a student answer",
    description=(
        "Record a student's answer to a quiz question. "
        "Returns whether the answer is correct and the recommended difficulty for the next question."
    ),
)
def submit_answer(
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
):
    # Look up the question
    question: Optional[QuizQuestion] = (
        db.query(QuizQuestion).filter_by(question_id=request.question_id).first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{request.question_id}' not found.",
        )

    # Check correctness (case-insensitive, strip whitespace)
    is_correct = request.selected_answer.strip().lower() == question.answer.strip().lower()

    # Persist the answer
    student_answer = StudentAnswer(
        student_id=request.student_id,
        question_id=request.question_id,
        selected_answer=request.selected_answer,
        is_correct=is_correct,
    )
    db.add(student_answer)
    db.commit()

    # Compute adaptive difficulty AFTER saving (so it includes this answer)
    performance = adaptive_service.compute_recommended_difficulty(
        student_id=request.student_id, db=db
    )

    return SubmitAnswerResponse(
        student_id=request.student_id,
        question_id=request.question_id,
        selected_answer=request.selected_answer,
        correct_answer=question.answer,
        is_correct=is_correct,
        recommended_difficulty=performance["recommended_difficulty"],
        message=(
            "Correct! Great job!" if is_correct
            else f"Incorrect. The correct answer is: {question.answer}"
        ),
    )


@router.get(
    "/student-performance/{student_id}",
    response_model=StudentPerformance,
    summary="Get student performance stats",
    description="Returns accuracy, streak info, current difficulty level, and recommended next difficulty.",
)
def get_student_performance(
    student_id: str,
    db: Session = Depends(get_db),
):
    perf = adaptive_service.compute_recommended_difficulty(student_id=student_id, db=db)

    total = perf["total_answered"]
    correct = perf["total_correct"]
    accuracy = round((correct / total * 100), 1) if total > 0 else 0.0

    return StudentPerformance(
        student_id=student_id,
        total_answered=total,
        total_correct=correct,
        total_incorrect=total - correct,
        accuracy_percent=accuracy,
        current_difficulty=perf["current_difficulty"],
        recent_streak=perf["recent_streak"],
        streak_type=perf["streak_type"],
    )
