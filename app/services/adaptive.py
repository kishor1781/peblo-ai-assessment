"""
Adaptive Difficulty Service

Algorithm:
- Tracks the student's last N answers from the StudentAnswer table
- 2+ consecutive correct  → bump difficulty UP   (easy → medium → hard)
- 2+ consecutive wrong    → bump difficulty DOWN  (hard → medium → easy)
- Otherwise              → keep current level

Returns the recommended difficulty level and current stats.
"""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import QuizQuestion, StudentAnswer

DIFFICULTY_ORDER = ["easy", "medium", "hard"]
STREAK_THRESHOLD = 2  # consecutive answers to trigger a change


def compute_recommended_difficulty(student_id: str, db: Session) -> dict:
    """
    Analyse a student's answer history and return:
      - current_difficulty (str)
      - recommended_difficulty (str)
      - recent_streak (int)
      - streak_type ("correct" | "incorrect" | "none")
      - total_answered (int)
      - total_correct (int)
    """
    # Fetch last 10 answers ordered by most recent first
    recent_answers: list[StudentAnswer] = (
        db.query(StudentAnswer)
        .filter_by(student_id=student_id)
        .order_by(desc(StudentAnswer.submitted_at))
        .limit(10)
        .all()
    )

    total_answered = db.query(StudentAnswer).filter_by(student_id=student_id).count()
    total_correct = db.query(StudentAnswer).filter_by(student_id=student_id, is_correct=True).count()

    if not recent_answers:
        return {
            "current_difficulty": "easy",
            "recommended_difficulty": "easy",
            "recent_streak": 0,
            "streak_type": "none",
            "total_answered": 0,
            "total_correct": 0,
        }

    # Determine current difficulty from the last question answered
    last_question: QuizQuestion | None = (
        db.query(QuizQuestion)
        .filter_by(question_id=recent_answers[0].question_id)
        .first()
    )
    current_difficulty = last_question.difficulty if last_question else "easy"

    # Calculate streak (based on most-recent answers, index 0 = newest)
    streak, streak_type = _calculate_streak(recent_answers)

    # Apply adaptive rule
    recommended_difficulty = _apply_adaptive_rule(
        current_difficulty, streak, streak_type
    )

    return {
        "current_difficulty": current_difficulty,
        "recommended_difficulty": recommended_difficulty,
        "recent_streak": streak,
        "streak_type": streak_type,
        "total_answered": total_answered,
        "total_correct": total_correct,
    }


def _calculate_streak(answers: list[StudentAnswer]) -> tuple[int, str]:
    """
    Count the length and type of the current streak from the most recent answer.
    """
    if not answers:
        return 0, "none"

    first_result = answers[0].is_correct
    streak = 1

    for ans in answers[1:]:
        if ans.is_correct == first_result:
            streak += 1
        else:
            break

    streak_type = "correct" if first_result else "incorrect"
    return streak, streak_type


def _apply_adaptive_rule(current: str, streak: int, streak_type: str) -> str:
    """
    Bump difficulty up or down based on streak.
    """
    if streak < STREAK_THRESHOLD:
        return current  # not enough data to change

    current_idx = DIFFICULTY_ORDER.index(current) if current in DIFFICULTY_ORDER else 0

    if streak_type == "correct":
        new_idx = min(current_idx + 1, len(DIFFICULTY_ORDER) - 1)
    elif streak_type == "incorrect":
        new_idx = max(current_idx - 1, 0)
    else:
        new_idx = current_idx

    return DIFFICULTY_ORDER[new_idx]
