# AI Interview Platform

A full-stack mock technical interview platform that uses **retrieval-augmented generation (RAG)** to ask relevant questions and an **LLM** to evaluate answers — simulating a real technical interview from start to finish.

---

## Overview

You pick a topic, the app asks you a relevant question, you answer it, and an AI interviewer scores your answer, gives feedback, and asks a natural follow-up — just like a real interview. After a few rounds, you get a summary with your overall score and the full transcript.

**Key features:**
- Secure signup/login with JWT authentication
- Semantic question retrieval via RAG (not keyword matching — finds relevant questions even with zero shared words)
- AI-generated scoring, feedback, and follow-up questions for every answer
- End-of-interview summary with overall score and full history
- Runs on free-tier tools only — no OpenAI key required

---

## How it works

```
   You                Frontend             Backend               AI Layer
 +------+          +-----------+        +-------------+      +--------------+
 | Pick |  ------> |  React    | -----> |  FastAPI    | ---> | RAG retrieval |
 | topic|          |  (Vite)   |        |  + Postgres |      | (ChromaDB)    |
 +------+          +-----------+        +-------------+      +------+-------+
                                                                      |
                                                                      v
                                                              +--------------+
                                                              |  Groq LLM    |
                                                              | (scoring +   |
                                                              |  follow-ups) |
                                                              +--------------+
```

**Step by step:**
1. You start an interview on a topic (e.g. "binary trees").
2. The backend embeds your topic and searches a curated question bank stored in **ChromaDB**, using **local, free sentence embeddings** — no API call needed for this step.
3. You submit an answer. The backend sends your question + answer to **Groq's LLM**, which returns a score (1–10), specific feedback, and a follow-up question.
4. Each follow-up is saved as a real question in **PostgreSQL**, so your full interview history is a genuine multi-question record — not just the last answer.
5. After 4 rounds (or if you end early), you get a summary: your average score and every Q&A pair.

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React (Vite) | Fast dev server, simple SPA |
| Backend | FastAPI | Async, auto-generated API docs, great for this scale |
| Database | PostgreSQL | Relational data (users -> sessions -> questions) fits naturally |
| Auth | JWT + bcrypt | Stateless auth, industry-standard password hashing |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) | Fully local and free — no API key needed for retrieval |
| Vector store | ChromaDB | Lightweight, zero-config semantic search |
| LLM | Groq API (Llama 3.1 8B) | Free tier, fast responses, OpenAI-compatible API |

---

## Project structure

```
ai-interview-platform/
├── backend/
│   ├── app/
│   │   ├── api/          → auth.py, interview.py (route handlers)
│   │   ├── core/         → database.py, security.py
│   │   ├── models/       → SQLAlchemy models
│   │   ├── schemas/      → Pydantic request/response types
│   │   ├── services/     → rag_service.py, interviewer_service.py, question_bank.json
│   │   └── main.py       → app entrypoint
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx        → auth screen, interview flow, summary screen
    │   └── main.jsx
    └── package.json
```

---

## Setup

### Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL (running locally)
- A free Groq API key from https://console.groq.com/keys (takes ~2 minutes to get)

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create the database:
```bash
createdb interview_platform
```

Set up your environment file:
```bash
cp .env.example .env
```
Then edit `.env` and fill in:
- `DATABASE_URL` — your Postgres connection string
- `SECRET_KEY` — any random string
- `GROQ_API_KEY` — your Groq key

Create the tables:
```bash
python3 -c "from app.core.database import Base, engine; from app.models import models; Base.metadata.create_all(bind=engine)"
```

Run the server:
```bash
uvicorn app.main:app --reload
```
API live at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```
App live at `http://localhost:5173`

---

## API reference

| Method | Endpoint | What it does |
|---|---|---|
| `POST` | `/auth/signup` | Create an account |
| `POST` | `/auth/login` | Log in, get a JWT |
| `GET` | `/auth/me` | Get the current user |
| `POST` | `/interview/start` | Start an interview on a topic |
| `POST` | `/interview/answer` | Submit an answer, get score + feedback + next question |
| `POST` | `/interview/{session_id}/end` | End early and get the summary |
| `GET` | `/interview/{session_id}` | Get the full history for one session |

---

## Design decisions worth knowing

- **Follow-up questions are persisted, not just displayed.** Each one becomes its own row in the database with its own score — so a session's history is a real multi-question transcript, not a single overwritten answer.
- **Interviews are capped at 4 rounds** (configurable via `MAX_ROUNDS` in `api/interview.py`), giving every interview a natural, scorable end point.
- **CORS is fully open** (`allow_origins=["*"]`) for local development. In production, this should be restricted to the actual frontend's origin.

---

## Possible next steps

- Upload a resume and use RAG over its content to tailor questions to the candidate's real background
- Swap the plain textarea for a real code editor (Monaco) with syntax highlighting
- Add a "past sessions" list in the frontend (the backend already supports this via `GET /interview/{session_id}`)
- Swap Groq for a fully local LLM (via Ollama) for a zero-API-cost, fully offline version
