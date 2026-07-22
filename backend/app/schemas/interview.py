from pydantic import BaseModel
from typing import Optional


class StartInterviewRequest(BaseModel):
    topic: str  # e.g. "binary trees", "Python REST APIs", "system design"


class AnswerRequest(BaseModel):
    session_id: int
    question_id: int
    answer_text: str


class QuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    user_answer: Optional[str] = None
    ai_feedback: Optional[str] = None
    score: Optional[float] = None

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    topic: Optional[str] = None
    status: str
    overall_score: Optional[float] = None
    feedback_summary: Optional[str] = None
    questions: list[QuestionOut] = []

    class Config:
        from_attributes = True


class StartInterviewResponse(BaseModel):
    session_id: int
    question_id: int
    question_text: str
    round_number: int
    max_rounds: int


class AnswerResponse(BaseModel):
    score: Optional[int]
    feedback: str
    follow_up_question: Optional[str] = None
    next_question_id: Optional[int] = None
    round_number: int
    max_rounds: int
    session_completed: bool
    overall_score: Optional[float] = None
