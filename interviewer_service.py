import os
from openai import OpenAI
from dotenv import load_dotenv
from app.services.rag_service import retrieve_relevant_questions

load_dotenv()

# Groq exposes an OpenAI-compatible API, so we just point the OpenAI client at Groq's endpoint
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# A fast, free-tier-friendly Groq model, good for quick interview-style responses
MODEL_NAME = "llama-3.1-8b-instant"


def start_interview_question(topic_or_context: str) -> dict:
    """
    Given a topic (e.g. 'binary trees') or resume context (e.g. 'Python Django REST APIs'),
    retrieves the most relevant question via RAG and returns it as the interview's opening question.
    """
    matches = retrieve_relevant_questions(topic_or_context, top_k=1)
    if not matches:
        raise ValueError("No relevant questions found in the question bank.")
    return matches[0]


def generate_follow_up(question: str, candidate_answer: str) -> str:
    """
    Given the original question and the candidate's answer, asks the LLM to act as a technical
    interviewer: it should ask ONE natural follow-up question based on what the candidate said.
    """
    system_prompt = (
        "You are a friendly but rigorous technical interviewer. "
        "Given an interview question and the candidate's answer, ask exactly ONE natural, "
        "specific follow-up question that probes deeper into their understanding "
        "(e.g. edge cases, time/space complexity, alternative approaches, or a related concept). "
        "Do not repeat the original question. Keep it to 1-2 sentences."
    )
    user_prompt = f"Original question: {question}\n\nCandidate's answer: {candidate_answer}"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()


def evaluate_answer(question: str, candidate_answer: str) -> dict:
    """
    Given a question and the candidate's answer, asks the LLM to score the answer (1-10)
    and give short, constructive feedback. Returns a dict with 'score' and 'feedback'.
    """
    system_prompt = (
        "You are a technical interview evaluator. Given a question and a candidate's answer, "
        "respond with EXACTLY two lines in this format, nothing else:\n"
        "SCORE: <integer 1-10>\n"
        "FEEDBACK: <2-3 sentences of constructive, specific feedback>"
    )
    user_prompt = f"Question: {question}\n\nCandidate's answer: {candidate_answer}"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=200,
    )

    content = response.choices[0].message.content.strip()

    # Parse the two expected lines out of the model's response
    score = None
    feedback = content
    for line in content.split("\n"):
        if line.upper().startswith("SCORE:"):
            try:
                score = int("".join(filter(str.isdigit, line)))
            except ValueError:
                score = None
        elif line.upper().startswith("FEEDBACK:"):
            feedback = line.split(":", 1)[1].strip()

    return {"score": score, "feedback": feedback}
