from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uuid
import os
import aiohttp
from typing import Optional
import uvicorn

# Import from other files
from session_manager import get_session, create_session, delete_session
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

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_id: Optional[str] = Cookie(None)):
    """Landing page with GitHub token authentication"""
    if session_id and await get_session(session_id):
        return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
    
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
        await create_session(session_id, api_key)
        
        # Set session cookie and redirect to setup page
        response = RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="session_id", value=session_id)
        return response
    
    except Exception as e:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": str(e)}
        )

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, session: dict = Depends(get_session)):
    """Page to setup interview parameters"""
    return templates.TemplateResponse(
        "setup.html", 
        {"request": request, "session": session}
    )

@app.post("/setup")
async def process_setup(
    request: Request,
    job_topic: str = Form(...),
    questions_per_round: int = Form(...),
    use_voice: bool = Form(False),
    session: dict = Depends(get_session)
):
    """Process interview setup parameters"""
    try:
        await setup_interview(session, job_topic, questions_per_round, use_voice)
        return RedirectResponse(url="/interview", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return templates.TemplateResponse(
            "setup.html", 
            {"request": request, "session": session, "error": str(e)}
        )

@app.get("/interview", response_class=HTMLResponse)
async def interview_page(request: Request, session: dict = Depends(get_session)):
    """Interview question and answer page"""
    # Generate a question if needed
    if not session.get("current_question"):
        await generate_question(session)
    
    return templates.TemplateResponse(
        "interview.html", 
        {"request": request, "session": session}
    )

@app.post("/submit-answer")
async def process_answer(
    request: Request,
    answer: str = Form(...),
    session: dict = Depends(get_session)
):
    """Process user's answer and generate feedback"""
    await submit_answer(session, answer)
    return RedirectResponse(url="/feedback", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/feedback", response_class=HTMLResponse)
async def feedback_page(request: Request, session: dict = Depends(get_session)):
    """Page to display feedback on user's answer"""
    return templates.TemplateResponse(
        "feedback.html", 
        {"request": request, "session": session}
    )

@app.post("/continue")
async def process_continue(
    request: Request,
    action: str = Form(...),
    session: dict = Depends(get_session)
):
    """Process user's decision to continue or end the interview"""
    if action == "continue":
        await continue_interview(session)
        return RedirectResponse(url="/interview", status_code=status.HTTP_303_SEE_OTHER)
    else:
        await end_interview(session)
        return RedirectResponse(url="/summary", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/summary", response_class=HTMLResponse)
async def summary_page(request: Request, session: dict = Depends(get_session)):
    """Summary page for the interview session"""
    return templates.TemplateResponse(
        "summary.html", 
        {"request": request, "session": session}
    )

@app.get("/logout")
async def logout(request: Request, session_id: str = Cookie(None)):
    """End session and clear cookies"""
    if session_id:
        await delete_session(session_id)
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="session_id")
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
