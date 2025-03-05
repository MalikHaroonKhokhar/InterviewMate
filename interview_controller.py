from chatbot import VoiceEnabledInterviewMate
from session_manager import update_session
import asyncio

# Create a cache for InterviewMate instances to avoid recreating them
interview_mates = {}

async def get_interview_mate(api_key: str) -> VoiceEnabledInterviewMate:
    """Get or create an InterviewMate instance for the given API key"""
    if api_key not in interview_mates:
        interview_mate = VoiceEnabledInterviewMate(api_key)
        interview_mates[api_key] = interview_mate
    return interview_mates[api_key]

async def setup_interview(session: dict, job_topic: str, questions_per_round: int, use_voice: bool) -> None:
    """Setup interview parameters"""
    # Update session with interview parameters
    await update_session(
        session["session_id"],  # Use session_id from the session object
        job_topic=job_topic,
        questions_per_round=questions_per_round,
        use_voice=use_voice,
        question_number=1,
        previous_questions=[],
        completed_questions=[]
    )

async def generate_question(session: dict) -> str:
    """Generate an interview question"""
    interview_mate = await get_interview_mate(session["api_key"])
    
    # Generate question using the InterviewMate
    question = interview_mate.generate_question(
        session["job_topic"],
        session["question_number"],
        session["previous_questions"]
    )
    
    # Update session with the new question
    await update_session(
        session["session_id"],  # Use session_id from the session object
        current_question=question,
        current_answer=None,
        feedback=None
    )
    
    return question

async def submit_answer(session: dict, answer: str) -> str:
    """Process answer and generate feedback"""
    interview_mate = await get_interview_mate(session["api_key"])
    
    # Store the answer
    await update_session(
        session["session_id"],  # Use session_id from the session object
        current_answer=answer
    )
    
    # Generate feedback
    feedback = interview_mate.generate_feedback(
        session["job_topic"],
        session["current_question"],
        answer
    )
    
    # Update session with feedback
    await update_session(
        session["session_id"],  # Use session_id from the session object
        feedback=feedback
    )
    
    # Add to completed questions
    completed_questions = session.get("completed_questions", [])
    completed_questions.append({
        "question": session["current_question"],
        "answer": answer,
        "feedback": feedback,
        "question_number": session["question_number"]
    })
    
    await update_session(
        session["session_id"],  # Use session_id from the session object
        completed_questions=completed_questions
    )
    
    return feedback

async def continue_interview(session: dict) -> None:
    """Continue to the next question"""
    # Add current question to previous questions list
    previous_questions = session.get("previous_questions", [])
    if session["current_question"] and session["current_question"] not in previous_questions:
        previous_questions.append(session["current_question"])
    
    # Update session for next question
    await update_session(
        session["session_id"],  # Use session_id from the session object
        previous_questions=previous_questions,
        question_number=session["question_number"] + 1,
        current_question=None,
        current_answer=None,
        feedback=None
    )
    
    # Check if we've reached the end of the round
    if session["question_number"] > session["questions_per_round"]:
        # Reset for next round if needed
        await update_session(
            session["session_id"],  # Use session_id from the session object
            question_number=1
        )

async def end_interview(session: dict) -> None:
    """End the interview session and prepare summary"""
    # Just mark that we've finished - the summary page will use completed_questions
    await update_session(
        session["session_id"],  # Use session_id from the session object
        interview_complete=True
    )