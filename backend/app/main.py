from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, interview
from app.core.database import Base, engine
from app.models import models
from app.services.rag_service import build_index

app = FastAPI(
    title="AI Interview Platform",
    description="A RAG-powered mock technical interview platform",
    version="0.1.0",
)

# Allow the React frontend (running on a different port during dev) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(interview.router)


@app.on_event("startup")
def on_startup():
    # Creates tables if they don't exist yet, and builds the RAG index if it's empty.
    # Safe to run every time the app starts (both locally and on a fresh deploy).
    Base.metadata.create_all(bind=engine)
    build_index()


@app.get("/")
def root():
    return {"message": "AI Interview Platform API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
