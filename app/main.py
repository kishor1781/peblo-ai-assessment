"""
Peblo AI Quiz Engine – FastAPI Application Entry Point
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import ingest as ingest_router
from app.routers import quiz as quiz_router
from app.routers import student as student_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Peblo AI Quiz Engine",
    description=(
        "A backend system that ingests educational PDFs, generates quiz questions "
        "using Google Gemini, and serves them through REST APIs with adaptive difficulty."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS (allow all origins for local dev)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    logger.info("Initializing database…")
    init_db()
    logger.info("Database ready ✓")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(ingest_router.router)
app.include_router(quiz_router.router)
app.include_router(student_router.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"], summary="Health check")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/", tags=["System"], include_in_schema=False)
def root():
    return {
        "message": "Welcome to the Peblo AI Quiz Engine!",
        "docs": "/docs",
        "health": "/health",
    }
