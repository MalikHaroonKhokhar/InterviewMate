from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uuid
import os
import aiohttp
from typing import Optional
import uvicorn
from pydantic import BaseModel

# Import from other files
from redis_session_manager import get_session, update_session, delete_session
from interview_controller import (
    setup_interview,
    generate_question,
    submit_answer,
    continue_interview,
    end_interview
)

# Create FastAPI app
app = FastAPI(title="InterviewMate Frontend")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class InterviewSetup(BaseModel):
    api_key: str
    job_topic: str
    questions_per_round: int = 5
    use_voice: bool = False

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_id: Optional[str] = Cookie(None)):
    """Landing page with API key authentication"""
    try:
        # Check if we have a valid session
        if session_id:
            session_data = await get_session(session_id)
            if session_data and session_data.get("api_key"):
                # If we have a valid session with API key, redirect to setup
                return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Error checking session: {str(e)}")
    
    # If no valid session or error, show login page
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "error": None}
    )

@app.post("/login")
async def login(request: Request, api_key: str = Form(...)):
    """Validate API key and create a session"""
    try:
        # Create a new session with the API key
        session_id = str(uuid.uuid4())
        success = await update_session(
            session_id,
            api_key=api_key,
            initialized=True
        )
        
        if not success:
            raise Exception("Failed to create session")
        
        # Set session cookie and redirect to setup page
        response = RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,  # Make cookie only accessible by server
            secure=True,    # Only send over HTTPS
            samesite="lax"  # Protect against CSRF
        )
        return response
    
    except Exception as e:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": str(e)}
        )

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(
    request: Request,
    session_id: str = Cookie(None)
):
    """Page to setup interview parameters"""
    if not session_id:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        # Get session data
        session_data = await get_session(session_id)
        if not session_data or not session_data.get("api_key"):
            # If no valid session or no API key, clear cookie and redirect to login
            response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            response.delete_cookie(key="session_id")
            return response
        
        # Check if interview is already set up
        if session_data.get("job_topic"):
            # If interview is already set up, redirect to interview page
            return RedirectResponse(url="/interview", status_code=status.HTTP_303_SEE_OTHER)
        
        return templates.TemplateResponse(
            "setup.html",
            {"request": request, "session": session_data}
        )
        
    except Exception as e:
        print(f"Error in setup page: {str(e)}")
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/setup")
async def process_setup(
    request: Request,
    job_topic: str = Form(...),
    questions_per_round: int = Form(...),
    use_voice: bool = Form(False),
    session_id: str = Cookie(None)
):
    """Process interview setup parameters"""
    if not session_id:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        # Get session data
        session_data = await get_session(session_id)
        if not session_data:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
        # Create session object for the controller
        session = {
            "session_id": session_id,
            "api_key": session_data.get("api_key")
        }
        
        # Setup the interview
        await setup_interview(session, job_topic, questions_per_round, use_voice)
        return RedirectResponse(url="/interview", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        return templates.TemplateResponse(
            "setup.html",
            {
                "request": request,
                "session": session_data,
                "error": str(e)
            }
        )

@app.get("/interview", response_class=HTMLResponse)
async def interview_page(
    request: Request,
    session_id: str = Cookie(None)
):
    """Interview question and answer page"""
    if not session_id:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Get session data
    session_data = await get_session(session_id)
    if not session_data:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Create session object for the controller
    session = {
        "session_id": session_id,
        "api_key": session_data.get("api_key")
    }
    
    # Generate a question if needed
    if not session_data.get("current_question"):
        question = await generate_question(session)
        if not question:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": "Failed to generate interview question. Please try again."
                }
            )
    
    # Get the latest session data after question generation
    session_data = await get_session(session_id)
    
    return templates.TemplateResponse(
        "interview.html",
        {"request": request, "session": session_data}
    )

@app.post("/submit-answer")
async def process_answer(
    request: Request,
    answer: str = Form(...),
    session_id: str = Cookie(None)
):
    """Process user's answer and generate feedback"""
    if not session_id:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        # Get session data
        session_data = await get_session(session_id)
        if not session_data:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
        # Create session object for the controller
        session = {
            "session_id": session_id,
            "api_key": session_data.get("api_key")
        }
        
        # Submit the answer
        feedback = await submit_answer(session, answer)
        if not feedback:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": "Failed to generate feedback. Please try again."
                }
            )
            
        return RedirectResponse(url="/feedback", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e)
            }
        )

@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(
    request: Request,
    session_id: str = Cookie(None)
):
    """Page to display feedback on user's answer"""
    if not session_id:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Get session data
    session_data = await get_session(session_id)
    if not session_data:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse(
        "feedback.html",
        {"request": request, "session": session_data}
    )

@app.post("/continue")
async def process_continue(
    request: Request,
    action: str = Form(...),
    session_id: str = Cookie(None)
):
    """Process user's decision to continue or end the interview"""
    if not session_id:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    try:
        # Get session data
        session_data = await get_session(session_id)
        if not session_data:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
        # Create session object for the controller
        session = {
            "session_id": session_id,
            "api_key": session_data.get("api_key")
        }
        
        if action == "continue":
            await continue_interview(session)
            return RedirectResponse(url="/interview", status_code=status.HTTP_303_SEE_OTHER)
        else:
            await end_interview(session)
            return RedirectResponse(url="/summary", status_code=status.HTTP_303_SEE_OTHER)
            
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e)
            }
        )

@app.get("/summary", response_class=HTMLResponse)
async def summary_page(
    request: Request,
    session_id: str = Cookie(None)
):
    """Summary page for the interview session"""
    if not session_id:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    # Get session data
    session_data = await get_session(session_id)
    if not session_data:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse(
        "summary.html",
        {"request": request, "session": session_data}
    )

@app.get("/logout")
async def logout(request: Request, session_id: str = Cookie(None)):
    """End session and clear cookies"""
    if session_id:
        await delete_session(session_id)
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="session_id")
    return response

@app.post("/interview/setup")
async def setup_new_interview(setup_data: InterviewSetup):
    try:
        # Create a new session
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "api_key": setup_data.api_key
        }
        
        # Initialize the interview
        await setup_interview(
            session,
            setup_data.job_topic,
            setup_data.questions_per_round,
            setup_data.use_voice
        )
        
        return {"session_id": session_id}
        
    except Exception as e:
        print(f"Error in setup_new_interview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/interview/{session_id}")
async def get_interview_question(session_id: str, api_key: str):
    try:
        # Create session object
        session = {
            "session_id": session_id,
            "api_key": api_key
        }
        
        # Generate question
        question = await generate_question(session)
        if not question:
            raise HTTPException(status_code=404, detail="Could not generate question")
            
        return {"question": question}
        
    except Exception as e:
        print(f"Error in get_interview_question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class AnswerSubmission(BaseModel):
    answer: str

@app.post("/interview/{session_id}/answer")
async def submit_interview_answer(session_id: str, api_key: str, submission: AnswerSubmission):
    try:
        session = {
            "session_id": session_id,
            "api_key": api_key
        }
        
        feedback = await submit_answer(session, submission.answer)
        if not feedback:
            raise HTTPException(status_code=404, detail="Could not generate feedback")
            
        return {"feedback": feedback}
        
    except Exception as e:
        print(f"Error in submit_interview_answer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interview/{session_id}/continue")
async def continue_to_next_question(session_id: str, api_key: str):
    try:
        session = {
            "session_id": session_id,
            "api_key": api_key
        }
        
        await continue_interview(session)
        return {"status": "success"}
        
    except Exception as e:
        print(f"Error in continue_to_next_question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interview/{session_id}/end")
async def end_interview_session(session_id: str, api_key: str):
    try:
        session = {
            "session_id": session_id,
            "api_key": api_key
        }
        
        await end_interview(session)
        return {"status": "success"}
        
    except Exception as e:
        print(f"Error in end_interview_session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
