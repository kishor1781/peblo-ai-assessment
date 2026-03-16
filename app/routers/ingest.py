"""
Ingest Router

POST /ingest  – Upload a PDF file for extraction, chunking, and storage.
GET  /sources – List all ingested source documents.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SourceDocument
from app.schemas import IngestResponse, SourceDocOut
from app.services import ingestion as ingestion_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Ingestion"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a PDF file",
    description=(
        "Upload an educational PDF. The system extracts text, cleans it, "
        "splits it into content chunks, and stores everything in the database."
    ),
)
async def ingest_pdf(
    file: UploadFile = File(..., description="PDF file to ingest"),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    # Check if already ingested (by filename)
    existing = db.query(SourceDocument).filter_by(filename=file.filename).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File '{file.filename}' has already been ingested as source '{existing.source_id}'. "
                   "Use POST /generate-quiz to create questions from it.",
        )

    file_bytes = await file.read()

    try:
        source_doc, chunks = ingestion_service.ingest_pdf(
            file_bytes=file_bytes,
            filename=file.filename,
            db=db,
        )
    except Exception as exc:
        logger.exception("Ingestion failed for %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {exc}",
        )

    return IngestResponse(
        source_id=source_doc.source_id,
        filename=source_doc.filename,
        grade=source_doc.grade,
        subject=source_doc.subject,
        chunks_created=len(chunks),
        message=f"Successfully ingested '{file.filename}' into {len(chunks)} content chunk(s).",
    )


@router.get(
    "/sources",
    response_model=list[SourceDocOut],
    summary="List all ingested PDF sources",
)
def list_sources(db: Session = Depends(get_db)):
    docs = db.query(SourceDocument).all()
    results = []
    for doc in docs:
        results.append(
            SourceDocOut(
                source_id=doc.source_id,
                filename=doc.filename,
                grade=doc.grade,
                subject=doc.subject,
                ingested_at=doc.ingested_at,
                chunk_count=len(doc.chunks),
            )
        )
    return results
