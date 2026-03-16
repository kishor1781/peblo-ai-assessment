"""
Content Ingestion Service

Handles:
1. PDF text extraction using pdfplumber
2. Text cleaning (whitespace, hyphenation, page numbers)
3. Chunking into ~300-word segments
4. Metadata inference from filename (grade, subject)
5. Persisting SourceDocument + ContentChunk records
"""

from __future__ import annotations

import io
import re
import uuid
from pathlib import Path
from typing import Optional

import pdfplumber
from sqlalchemy.orm import Session

from app.models import ContentChunk, SourceDocument

# ---------------------------------------------------------------------------
# Filename → metadata mapping
# ---------------------------------------------------------------------------

FILENAME_META: dict[str, dict] = {
    "grade1": {"grade": 1},
    "grade2": {"grade": 2},
    "grade3": {"grade": 3},
    "grade4": {"grade": 4},
    "grade5": {"grade": 5},
    "math": {"subject": "Math"},
    "science": {"subject": "Science"},
    "english": {"subject": "English"},
    "history": {"subject": "History"},
    "numbers": {"topic_hint": "Numbers"},
    "shapes": {"topic_hint": "Shapes"},
    "plants": {"topic_hint": "Plants and Animals"},
    "grammar": {"topic_hint": "Grammar and Vocabulary"},
}

CHUNK_WORD_LIMIT = 300


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_pdf(
    file_bytes: bytes,
    filename: str,
    db: Session,
) -> tuple[SourceDocument, list[ContentChunk]]:
    """
    Extract, clean, chunk and store content from a PDF file.

    Returns:
        (SourceDocument, list[ContentChunk]) — persisted DB objects.
    """
    meta = _parse_filename_meta(filename)

    # Generate a stable source_id based on filename
    source_id = _generate_source_id(filename, db)

    # Extract raw text from PDF
    raw_text = _extract_text(file_bytes)

    # Clean text
    clean_text = _clean_text(raw_text)

    # Split into topic-aware chunks
    chunks_text = _chunk_text(clean_text)

    # Persist source document
    source_doc = SourceDocument(
        source_id=source_id,
        filename=filename,
        grade=meta.get("grade"),
        subject=meta.get("subject"),
    )
    db.add(source_doc)
    db.flush()  # get id without full commit

    # Persist chunks
    chunk_records: list[ContentChunk] = []
    for idx, chunk_text in enumerate(chunks_text, start=1):
        chunk_id = f"{source_id}_CH_{idx:02d}"
        topic = _infer_topic(chunk_text, meta.get("topic_hint"))

        chunk = ContentChunk(
            chunk_id=chunk_id,
            source_id=source_id,
            chunk_index=idx,
            grade=meta.get("grade"),
            subject=meta.get("subject"),
            topic=topic,
            text=chunk_text,
        )
        db.add(chunk)
        chunk_records.append(chunk)

    db.commit()
    db.refresh(source_doc)
    return source_doc, chunk_records


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_source_id(filename: str, db: Session) -> str:
    """Generate sequential SRC_001, SRC_002 … IDs."""
    existing_count = db.query(SourceDocument).count()
    return f"SRC_{existing_count + 1:03d}"


def _parse_filename_meta(filename: str) -> dict:
    """Extract grade, subject, topic_hint from filename tokens."""
    name_lower = filename.lower()
    meta: dict = {}
    for token, values in FILENAME_META.items():
        if token in name_lower:
            meta.update(values)
    return meta


def _extract_text(file_bytes: bytes) -> str:
    """Extract all text from a PDF using pdfplumber."""
    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return "\n".join(pages)


def _clean_text(text: str) -> str:
    """
    Clean extracted PDF text:
    - Normalize whitespace
    - Remove page numbers (standalone digits)
    - Fix hyphenated line breaks
    - Remove repeated blank lines
    """
    # Fix hyphenated line breaks: "tri-\nangle" → "triangle"
    text = re.sub(r"-\n", "", text)

    # Remove standalone page-number lines (e.g., "\n3\n")
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _chunk_text(text: str, word_limit: int = CHUNK_WORD_LIMIT) -> list[str]:
    """
    Split text into chunks of roughly `word_limit` words.
    Tries to break on paragraph boundaries first.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current_words: list[str] = []

    for para in paragraphs:
        para_words = para.split()
        # If adding this paragraph would exceed limit, flush current buffer
        if current_words and len(current_words) + len(para_words) > word_limit:
            chunks.append(" ".join(current_words))
            current_words = []
        current_words.extend(para_words)

    if current_words:
        chunks.append(" ".join(current_words))

    # If no meaningful split happened (single huge paragraph), hard-split by words
    if not chunks:
        words = text.split()
        chunks = [
            " ".join(words[i : i + word_limit])
            for i in range(0, len(words), word_limit)
        ]

    return [c for c in chunks if c.strip()]


def _infer_topic(text: str, topic_hint: Optional[str] = None) -> str:
    """
    Infer the topic of a chunk from keyword matching.
    Falls back to the filename topic_hint.
    """
    lower = text.lower()

    topic_keywords = {
        "Shapes": ["triangle", "circle", "square", "rectangle", "shape", "sides", "corners"],
        "Numbers": ["count", "number", "addition", "subtract", "plus", "minus", "digit"],
        "Plants": ["plant", "leaf", "root", "stem", "flower", "photosynthesis", "seed"],
        "Animals": ["animal", "mammal", "reptile", "bird", "fish", "insect", "habitat"],
        "Grammar": ["noun", "verb", "adjective", "sentence", "pronoun", "grammar"],
        "Vocabulary": ["word", "vocabulary", "meaning", "synonym", "antonym", "definition"],
        "Punctuation": ["comma", "period", "exclamation", "question mark", "punctuation"],
    }

    best_topic = topic_hint or "General"
    best_count = 0

    for topic, keywords in topic_keywords.items():
        count = sum(1 for kw in keywords if kw in lower)
        if count > best_count:
            best_count = count
            best_topic = topic

    return best_topic
