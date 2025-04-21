from chatbot import VoiceEnabledInterviewMate
from redis_session_manager import update_session, get_session
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
    # Make sure we have the required session_id and api_key
    if "session_id" not in session or "api_key" not in session:
        print("Error: Missing session_id or api_key in session")
        return None

    # Initialize session with interview parameters
    session_data = {
        "api_key": session["api_key"],
        "job_topic": job_topic,
        "questions_per_round": questions_per_round,
        "use_voice": use_voice,
        "question_number": 1,
        "previous_questions": [],
        "completed_questions": []
    }
    
    print(f"Setting up interview with data: {session_data}")  # Debug print
    
    # Update session with interview parameters
    success = await update_session(
        session["session_id"],
        **session_data
    )
    
    if not success:
        print("Error: Failed to update session in Redis")
        return None

async def generate_question(session: dict) -> str:
    """Generate an interview question"""
    try:
        # Validate input session
        if not session:
            print("Error: Session is None or empty")
            return None
            
        if not isinstance(session, dict):
            print(f"Error: Session is not a dictionary, got {type(session)}")
            return None
            
        if "session_id" not in session:
            print("Error: No session_id in session object")
            return None
            
        print(f"Attempting to generate question for session: {session}")  # Debug print
        
        # First, get the latest session data from Redis
        session_data = await get_session(session["session_id"])
        if not session_data:
            print(f"Error: No session data found in Redis for session_id: {session['session_id']}")
            return None
        
        # Ensure we have all required fields
        if "api_key" not in session_data:
            print("Error: No api_key in session data")
            return None
            
        if "job_topic" not in session_data:
            print("Error: No job_topic in session data")
            return None

        print(f"Retrieved session data: {session_data}")  # Debug print

        interview_mate = await get_interview_mate(session_data["api_key"])
        
        # Generate question using the InterviewMate
        question = interview_mate.generate_question(
            session_data["job_topic"],
            session_data.get("question_number", 1),
            session_data.get("previous_questions", [])
        )
        
        if not question:
            print("Error: Failed to generate question from InterviewMate")
            return None
            
        print(f"Generated question: {question}")  # Debug print
        
        # Update session with the new question
        update_success = await update_session(
            session["session_id"],
            current_question=question,
            current_answer=None,
            feedback=None
        )
        
        if not update_success:
            print("Error: Failed to update session with new question")
            return None
        
        return question
        
    except Exception as e:
        print(f"Unexpected error in generate_question: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

async def submit_answer(session: dict, answer: str) -> str:
    """Process answer and generate feedback"""
    # Get the latest session data
    session_data = await get_session(session["session_id"])
    if not session_data:
        print("Error: No session data found in Redis")
        return None
    
    interview_mate = await get_interview_mate(session_data["api_key"])
    
    # Store the answer
    await update_session(
        session["session_id"],
        current_answer=answer
    )
    
    # Generate feedback
    feedback = interview_mate.generate_feedback(
        session_data["job_topic"],
        session_data["current_question"],
        answer
    )
    
    # Update session with feedback
    await update_session(
        session["session_id"],
        feedback=feedback
    )
    
    # Add to completed questions
    completed_questions = session_data.get("completed_questions", [])
    completed_questions.append({
        "question": session_data["current_question"],
        "answer": answer,
        "feedback": feedback,
        "question_number": session_data["question_number"]
    })
    
    # Update completed questions in session
    await update_session(
        session["session_id"],
        completed_questions=completed_questions
    )
    
    return feedback

async def continue_interview(session: dict) -> None:
    """Continue to the next question"""
    # Get the latest session data
    session_data = await get_session(session["session_id"])
    if not session_data:
        print("Error: No session data found in Redis")
        return None
    
    # Add current question to previous questions list
    previous_questions = session_data.get("previous_questions", [])
    if session_data.get("current_question") and session_data["current_question"] not in previous_questions:
        previous_questions.append(session_data["current_question"])
    
    # Calculate next question number
    next_question_number = session_data.get("question_number", 1) + 1
    
    # Check if we've reached the end of the round
    if next_question_number > session_data.get("questions_per_round", 0):
        next_question_number = 1
    
    # Update session for next question
    await update_session(
        session["session_id"],
        previous_questions=previous_questions,
        question_number=next_question_number,
        current_question=None,
        current_answer=None,
        feedback=None
    )

async def end_interview(session: dict) -> None:
    """End the interview session and prepare summary"""
    # Just mark that we've finished - the summary page will use completed_questions
    await update_session(
        session["session_id"],  # Use session_id from the session object
        interview_complete=True
    )