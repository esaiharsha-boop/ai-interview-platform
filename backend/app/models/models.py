from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    resume_text = Column(Text, nullable=True)  # extracted text from uploaded resume
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    interviews = relationship("InterviewSession", back_populates="user")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String, nullable=True)  # e.g. "Backend Engineer", "DSA - Arrays"
    status = Column(String, default="in_progress")  # in_progress / completed
    overall_score = Column(Float, nullable=True)
    feedback_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="interviews")
    questions = relationship("InterviewQuestion", back_populates="session")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String, default="coding")  # coding / follow_up / behavioral
    user_answer = Column(Text, nullable=True)
    submitted_code = Column(Text, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="questions")
