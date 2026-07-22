from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, InterviewSession, InterviewQuestion
from app.schemas.interview import (
    StartInterviewRequest,
    AnswerRequest,
    StartInterviewResponse,
    AnswerResponse,
    SessionOut,
)
from app.services.interviewer_service import (
    start_interview_question,
    generate_follow_up,
    evaluate_answer,
)

router = APIRouter(prefix="/interview", tags=["interview"])

# Total number of questions (initial + follow-ups) before an interview wraps up automatically
MAX_ROUNDS = 4


def _finish_session(db: Session, session: InterviewSession):
    """Marks a session completed and computes its overall score from all scored questions."""
    questions = db.query(InterviewQuestion).filter(InterviewQuestion.session_id == session.id).all()
    scored = [q.score for q in questions if q.score is not None]
    overall = sum(scored) / len(scored) if scored else None

    session.status = "completed"
    session.overall_score = overall
    session.feedback_summary = f"Completed {len(questions)} question(s) on '{session.topic}'."
    db.commit()
    db.refresh(session)
    return session


@router.post("/start", response_model=StartInterviewResponse)
def start_interview(
    request: StartInterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = InterviewSession(user_id=current_user.id, topic=request.topic, status="in_progress")
    db.add(session)
    db.commit()
    db.refresh(session)

    question_data = start_interview_question(request.topic)

    question = InterviewQuestion(
        session_id=session.id,
        question_text=question_data["question"],
        question_type="coding",
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return StartInterviewResponse(
        session_id=session.id,
        question_id=question.id,
        question_text=question.question_text,
        round_number=1,
        max_rounds=MAX_ROUNDS,
    )


@router.post("/answer", response_model=AnswerResponse)
def submit_answer(
    request: AnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(InterviewSession.id == request.session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="This interview has already ended")

    question = db.query(InterviewQuestion).filter(InterviewQuestion.id == request.question_id).first()
    if not question or question.session_id != session.id:
        raise HTTPException(status_code=404, detail="Question not found in this session")

    question.user_answer = request.answer_text

    evaluation = evaluate_answer(question.question_text, request.answer_text)
    question.ai_feedback = evaluation["feedback"]
    question.score = evaluation["score"]
    db.commit()

    current_round = db.query(InterviewQuestion).filter(InterviewQuestion.session_id == session.id).count()

    # If we've hit the round limit, end the session here instead of generating another follow-up
    if current_round >= MAX_ROUNDS:
        finished = _finish_session(db, session)
        return AnswerResponse(
            score=evaluation["score"],
            feedback=evaluation["feedback"],
            follow_up_question=None,
            next_question_id=None,
            round_number=current_round,
            max_rounds=MAX_ROUNDS,
            session_completed=True,
            overall_score=finished.overall_score,
        )

    # Otherwise generate the next follow-up and persist it as a real question for the next round
    follow_up_text = generate_follow_up(question.question_text, request.answer_text)
    follow_up_question = InterviewQuestion(
        session_id=session.id,
        question_text=follow_up_text,
        question_type="follow_up",
    )
    db.add(follow_up_question)
    db.commit()
    db.refresh(follow_up_question)

    return AnswerResponse(
        score=evaluation["score"],
        feedback=evaluation["feedback"],
        follow_up_question=follow_up_text,
        next_question_id=follow_up_question.id,
        round_number=current_round + 1,
        max_rounds=MAX_ROUNDS,
        session_completed=False,
        overall_score=None,
    )


@router.post("/{session_id}/end", response_model=SessionOut)
def end_interview(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Interview session not found")

    if session.status != "completed":
        _finish_session(db, session)

    return session


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session
