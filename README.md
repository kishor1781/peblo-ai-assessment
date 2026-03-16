# Peblo AI Quiz Engine

> **Backend Engineer Challenge** — Content Ingestion + Adaptive Quiz Engine

A FastAPI-based backend that ingests educational PDFs, extracts and chunks their content, generates quiz questions using **Google Gemini**, stores everything in **SQLite**, and serves quizzes through REST APIs with **adaptive difficulty adjustment**.

---

## Architecture

```
PDFs  ──►  Ingestion Service  ──►  SQLite Database
                                        │
               Gemini LLM  ◄───  Quiz Generation Service
                                        │
                             FastAPI REST API
                                        │
                      Student Answer + Adaptive Difficulty
```

### Components

| Component | File(s) | Description |
|-----------|---------|-------------|
| FastAPI app | `app/main.py` | Entry point, CORS, startup |
| Config | `app/config.py` | `.env` loading via pydantic-settings |
| Database | `app/database.py` | SQLAlchemy engine + session |
| Models | `app/models.py` | 4 ORM tables |
| Schemas | `app/schemas.py` | Pydantic request/response |
| Ingestion | `app/services/ingestion.py` | PDF extract → clean → chunk |
| LLM | `app/services/llm.py` | Gemini integration + prompting |
| Quiz | `app/services/quiz.py` | LLM orchestration + storage |
| Adaptive | `app/services/adaptive.py` | Difficulty adjustment logic |
| Routers | `app/routers/` | `ingest.py`, `quiz.py`, `student.py` |

### Database Schema

```
source_documents
  ├── source_id (PK)
  ├── filename, grade, subject, ingested_at

content_chunks
  ├── chunk_id (PK)
  ├── source_id → source_documents
  ├── chunk_index, grade, subject, topic, text

quiz_questions
  ├── question_id (PK)
  ├── chunk_id → content_chunks
  ├── question, question_type, options_json, answer, difficulty

student_answers
  ├── id (PK)
  ├── student_id, question_id → quiz_questions
  ├── selected_answer, is_correct, submitted_at
```

---

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- A **Google Gemini API key** (free at [aistudio.google.com](https://aistudio.google.com/))

### 2. Install Dependencies

```bash
cd "peblo ass"
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your Gemini API key
GEMINI_API_KEY=your_actual_key_here
DATABASE_URL=sqlite:///./peblo.db
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

The server starts at **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/sources` | List all ingested PDFs |
| `POST` | `/ingest` | Upload a PDF for ingestion |
| `POST` | `/generate-quiz` | Generate quiz questions via LLM |
| `GET` | `/quiz` | Retrieve questions (with filters) |
| `POST` | `/submit-answer` | Submit a student answer |
| `GET` | `/student-performance/{id}` | Get student stats + difficulty |

---

## Testing the Endpoints

### Step 1 – Health Check
```bash
curl http://localhost:8000/health
```

### Step 2 – Ingest PDFs
```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@data/peblo_pdf_grade1_math_numbers.pdf"

curl -X POST http://localhost:8000/ingest \
  -F "file=@data/peblo_pdf_grade3_science_plants_animals.pdf"

curl -X POST http://localhost:8000/ingest \
  -F "file=@data/peblo_pdf_grade4_english_grammar.pdf"
```

### Step 3 – Generate Quiz Questions
```bash
curl -X POST http://localhost:8000/generate-quiz \
  -H "Content-Type: application/json" \
  -d '{"source_id": "SRC_001", "max_questions_per_chunk": 3}'
```

### Step 4 – Retrieve Quiz
```bash
# All questions
curl "http://localhost:8000/quiz"

# Filtered by topic and difficulty
curl "http://localhost:8000/quiz?topic=Shapes&difficulty=easy"

# Filtered by grade and subject
curl "http://localhost:8000/quiz?grade=1&subject=Math"

# By question type
curl "http://localhost:8000/quiz?question_type=MCQ"
```

### Step 5 – Submit a Student Answer
```bash
curl -X POST http://localhost:8000/submit-answer \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "S001",
    "question_id": "<question_id_from_quiz>",
    "selected_answer": "3"
  }'
```

### Step 6 – Check Student Performance & Adaptive Difficulty
```bash
curl http://localhost:8000/student-performance/S001
```

---

## Adaptive Difficulty Algorithm

The system tracks students' answer streaks and adjusts difficulty automatically:

```
Correct ×2 in a row  →  difficulty INCREASES  (easy → medium → hard)
Wrong   ×2 in a row  →  difficulty DECREASES  (hard → medium → easy)
Otherwise            →  difficulty stays the same
```

The `POST /submit-answer` response includes `recommended_difficulty` for the next question.
The `GET /student-performance/{id}` shows the full stats breakdown.

---

## Sample Outputs

See the `sample_outputs/` directory for:
- `ingestion_response.json` — response from `/ingest`
- `quiz_questions.json` — sample generated questions
- `submit_answer_response.json` — response from `/submit-answer`
- `student_performance.json` — response from `/student-performance`

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ Yes |
| `DATABASE_URL` | SQLAlchemy DB URL (SQLite default) | Optional |
| `DEBUG` | Enable debug mode | Optional |

---

## Technology Stack

- **Backend**: Python 3.11 + FastAPI + Uvicorn
- **Database**: SQLite + SQLAlchemy 2.0 ORM
- **LLM**: Google Gemini (`gemini-1.5-flash`) via `google-generativeai`
- **PDF Parsing**: `pdfplumber`
- **Validation**: Pydantic v2

---

## Project Structure

```
peblo ass/
├── app/
│   ├── main.py              ← FastAPI app entry point
│   ├── config.py            ← Settings from .env
│   ├── database.py          ← SQLAlchemy engine + session
│   ├── models.py            ← ORM models
│   ├── schemas.py           ← Pydantic schemas
│   ├── services/
│   │   ├── ingestion.py     ← PDF extraction + chunking
│   │   ├── llm.py           ← Gemini LLM integration
│   │   ├── quiz.py          ← Quiz generation orchestration
│   │   └── adaptive.py      ← Adaptive difficulty logic
│   └── routers/
│       ├── ingest.py        ← POST /ingest, GET /sources
│       ├── quiz.py          ← POST /generate-quiz, GET /quiz
│       └── student.py       ← POST /submit-answer, GET /student-performance
├── data/                    ← PDF files
│   ├── peblo_pdf_grade1_math_numbers.pdf
│   ├── peblo_pdf_grade3_science_plants_animals.pdf
│   └── peblo_pdf_grade4_english_grammar.pdf
├── sample_outputs/          ← Example JSON responses
├── .env.example             ← Environment template
├── requirements.txt         ← Python dependencies
└── README.md
```
