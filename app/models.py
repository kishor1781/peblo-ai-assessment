"""
SQLAlchemy ORM models for Peblo AI Quiz Engine.

Tables:
    source_documents  – One record per ingested PDF
    content_chunks    – Text segments extracted from a source document
    quiz_questions    – LLM-generated questions linked to a chunk
    student_answers   – Student submissions with correctness tracking
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Source Documents
# ---------------------------------------------------------------------------

class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["ContentChunk"]] = relationship("ContentChunk", back_populates="source_document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SourceDocument source_id={self.source_id} filename={self.filename}>"


# ---------------------------------------------------------------------------
# Content Chunks
# ---------------------------------------------------------------------------

class ContentChunk(Base):
    __tablename__ = "content_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("source_documents.source_id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    source_document: Mapped["SourceDocument"] = relationship("SourceDocument", back_populates="chunks")
    questions: Mapped[list["QuizQuestion"]] = relationship("QuizQuestion", back_populates="chunk", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ContentChunk chunk_id={self.chunk_id} topic={self.topic}>"


# ---------------------------------------------------------------------------
# Quiz Questions
# ---------------------------------------------------------------------------

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, default=_new_uuid)
    chunk_id: Mapped[str] = mapped_column(String(64), ForeignKey("content_chunks.chunk_id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)   # MCQ | TrueFalse | FillBlank
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)    # JSON array, only for MCQ/TrueFalse
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False, default="easy")  # easy | medium | hard
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunk: Mapped["ContentChunk"] = relationship("ContentChunk", back_populates="questions")
    student_answers: Mapped[list["StudentAnswer"]] = relationship("StudentAnswer", back_populates="question")

    def __repr__(self) -> str:
        return f"<QuizQuestion question_id={self.question_id} type={self.question_type} difficulty={self.difficulty}>"


# ---------------------------------------------------------------------------
# Student Answers
# ---------------------------------------------------------------------------

class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(64), ForeignKey("quiz_questions.question_id"), nullable=False)
    selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    question: Mapped["QuizQuestion"] = relationship("QuizQuestion", back_populates="student_answers")

    def __repr__(self) -> str:
        return f"<StudentAnswer student_id={self.student_id} question_id={self.question_id} correct={self.is_correct}>"
