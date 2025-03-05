from typing import Dict, Optional
from fastapi import Cookie, HTTPException, Request, Depends
import asyncio

# In-memory session storage
# In production, use Redis or another session store
sessions: Dict[str, dict] = {}

async def get_session_by_id(session_id: str) -> Optional[dict]:
    """Get session data for the given session ID"""
    session = sessions.get(session_id)
    if not session:
        return None
    return session

async def get_session(session_id: Optional[str] = Cookie(None)):
    """FastAPI dependency to get session from cookie"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    return session

async def create_session(session_id: str, api_key: str) -> dict:
    """Create a new session with the given API key"""
    # Validate API key if needed
    # For simplicity, we're just storing it, but you could test it against the chatbot here
    
    session = {
        "session_id": session_id,  # Add session_id to the session data
        "api_key": api_key,
        "job_topic": None,
        "use_voice": False,
        "questions_per_round": 3,
        "question_number": 1,
        "previous_questions": [],
        "current_question": None,
        "current_answer": None,
        "feedback": None,
        "completed_questions": []  # Store question-answer-feedback triplets
    }
    
    sessions[session_id] = session
    return session

async def update_session(session_id: str, **kwargs) -> dict:
    """Update session with the given key-value pairs"""
    if session_id not in sessions:
        raise KeyError(f"Session {session_id} not found")
    
    for key, value in kwargs.items():
        sessions[session_id][key] = value
    
    return sessions[session_id]

async def delete_session(session_id: str) -> None:
    """Delete the session with the given ID"""
    if session_id in sessions:
        del sessions[session_id]