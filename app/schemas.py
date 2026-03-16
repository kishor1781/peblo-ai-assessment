"""
Pydantic schemas for request validation and response serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class IngestResponse(BaseModel):
    source_id: str
    filename: str
    grade: Optional[int]
    subject: Optional[str]
    chunks_created: int
    message: str


# ---------------------------------------------------------------------------
# Content Chunks
# ---------------------------------------------------------------------------

class ChunkOut(BaseModel):
    chunk_id: str
    source_id: str
    chunk_index: int
    grade: Optional[int]
    subject: Optional[str]
    topic: Optional[str]
    text: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Quiz Generation
# ---------------------------------------------------------------------------

class GenerateQuizRequest(BaseModel):
    source_id: str = Field(..., description="Source document ID to generate questions from")
    max_questions_per_chunk: int = Field(default=3, ge=1, le=10)


class GenerateQuizResponse(BaseModel):
    source_id: str
    questions_generated: int
    message: str


# ---------------------------------------------------------------------------
# Quiz Questions
# ---------------------------------------------------------------------------

class QuestionOut(BaseModel):
    question_id: str
    chunk_id: str
    question: str
    question_type: str
    options: Optional[List[str]] = None
    answer: str
    difficulty: str
    topic: Optional[str]
    grade: Optional[int]
    subject: Optional[str]

    model_config = {"from_attributes": True}


class QuizListResponse(BaseModel):
    total: int
    questions: List[QuestionOut]


# ---------------------------------------------------------------------------
# Student Answers
# ---------------------------------------------------------------------------

class SubmitAnswerRequest(BaseModel):
    student_id: str = Field(..., description="Unique student identifier")
    question_id: str = Field(..., description="The ID of the question being answered")
    selected_answer: str = Field(..., description="The student's chosen answer")


class SubmitAnswerResponse(BaseModel):
    student_id: str
    question_id: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    recommended_difficulty: str
    message: str


# ---------------------------------------------------------------------------
# Student Performance
# ---------------------------------------------------------------------------

class StudentPerformance(BaseModel):
    student_id: str
    total_answered: int
    total_correct: int
    total_incorrect: int
    accuracy_percent: float
    current_difficulty: str
    recent_streak: int
    streak_type: str   # "correct" | "incorrect" | "none"


# ---------------------------------------------------------------------------
# Source Documents
# ---------------------------------------------------------------------------

class SourceDocOut(BaseModel):
    source_id: str
    filename: str
    grade: Optional[int]
    subject: Optional[str]
    ingested_at: datetime
    chunk_count: int

    model_config = {"from_attributes": True}
