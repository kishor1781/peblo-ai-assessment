"""
Quiz Generation Service

Orchestrates calling the LLM for each content chunk and persisting
the resulting QuizQuestion records to the database.
"""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.models import ContentChunk, QuizQuestion, SourceDocument
from app.services import llm as llm_service

logger = logging.getLogger(__name__)

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]


def generate_quiz_for_source(
    source_id: str,
    db: Session,
    max_questions_per_chunk: int = 3,
) -> list[QuizQuestion]:
    """
    Generate quiz questions for all chunks of a source document.
    Questions are stored in the DB and returned.
    """
    source_doc: SourceDocument | None = (
        db.query(SourceDocument).filter_by(source_id=source_id).first()
    )
    if not source_doc:
        raise ValueError(f"Source document '{source_id}' not found.")

    chunks: list[ContentChunk] = (
        db.query(ContentChunk)
        .filter_by(source_id=source_id)
        .order_by(ContentChunk.chunk_index)
        .all()
    )

    if not chunks:
        raise ValueError(f"No content chunks found for source '{source_id}'.")

    all_questions: list[QuizQuestion] = []

    # Fetch existing question texts for dedup
    existing_q_texts = [
        q.question
        for q in db.query(QuizQuestion.question)
        .join(ContentChunk, QuizQuestion.chunk_id == ContentChunk.chunk_id)
        .filter(ContentChunk.source_id == source_id)
        .all()
    ]

    for chunk in chunks:
        logger.info("Generating questions for chunk: %s", chunk.chunk_id)

        # Determine difficulty based on chunk index (easy → medium → hard cycling)
        difficulty_index = (chunk.chunk_index - 1) % len(DIFFICULTY_LEVELS)
        difficulty = DIFFICULTY_LEVELS[difficulty_index]

        raw_questions = llm_service.generate_questions_for_chunk(
            chunk_text=chunk.text,
            chunk_id=chunk.chunk_id,
            difficulty=difficulty,
            count=max_questions_per_chunk,
            existing_questions=existing_q_texts,
        )

        for q_data in raw_questions:
            question_id = f"Q_{chunk.chunk_id}_{str(uuid.uuid4())[:8]}"
            options_json = json.dumps(q_data["options"]) if q_data.get("options") else None

            question = QuizQuestion(
                question_id=question_id,
                chunk_id=chunk.chunk_id,
                question=q_data["question"],
                question_type=q_data["question_type"],
                options_json=options_json,
                answer=q_data["answer"],
                difficulty=q_data.get("difficulty", difficulty),
                topic=chunk.topic,
                grade=chunk.grade,
                subject=chunk.subject,
            )
            db.add(question)
            all_questions.append(question)
            existing_q_texts.append(q_data["question"])  # update dedup list

    db.commit()
    logger.info("Generated %d questions for source %s", len(all_questions), source_id)
    return all_questions
