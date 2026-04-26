from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
import random
import base64
import json
import google.generativeai as genai
from database import get_db
from models import User, HabitLog, AvatarState
 
router = APIRouter(prefix="/tasks", tags=["tasks"])
 
# ─── Configure Gemini ─────────────────────────────────────────────────────────
 
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini = genai.GenerativeModel("gemini-1.5-flash")
 
# ─── Default Tasks ────────────────────────────────────────────────────────────
 
DEFAULT_TASKS = {
    "sleep": [
        "Take a photo of your bed made in the morning",
        "Take a photo of your phone on do not disturb before 11pm",
        "Take a photo of your sleep tracker or alarm set for 8 hours"
    ],
    "physique": [
        "Take a photo of yourself at the gym or working out",
        "Take a photo of your completed workout logged in an app",
        "Take a photo of yourself on a walk or run outside"
    ],
    "water": [
        "Take a photo of your water bottle filled up",
        "Take a photo of 8 empty glasses or a full water jug",
        "Take a photo of your water intake tracker"
    ],
    "nutrition": [
        "Take a photo of your healthy meal",
        "Take a photo of your plate with vegetables on it",
        "Take a photo of your healthy breakfast"
    ],
    "mood": [
        "Take a photo of your journal with 3 things you are grateful for written down",
        "Take a photo of yourself smiling",
        "Take a photo of something that made you happy today"
    ],
    "school": [
        "Take a photo of your completed homework",
        "Take a photo of your notes from studying",
        "Take a photo of your finished assignment"
    ],
    "work": [
        "Take a photo of your completed to do list",
        "Take a photo of your clean and organised desk",
        "Take a photo of your cleared email inbox"
    ],
    "mindfulness": [
        "Take a photo of your meditation app showing a completed session",
        "Take a photo of yourself outside in nature or fresh air",
        "Take a photo of your journal after writing"
    ],
    "screentime": [
        "Take a photo of your screen time showing reduced usage",
        "Take a photo of your phone face down during a meal",
        "Take a photo of your phone showing app limits enabled"
    ],
    "social": [
        "Take a photo of a meal or activity with friends or family",
        "Take a photo of a handwritten note or card you made for someone",
        "Take a photo of yourself and a friend or family member together"
    ]
}
 
VALID_CATEGORIES = list(DEFAULT_TASKS.keys())
 
# ─── Request / Response Models ────────────────────────────────────────────────
 
class TaskGenerateRequest(BaseModel):
    categories: List[str]
 
class TaskCompleteRequest(BaseModel):
    category: str
    task: str
    image: str  # base64 encoded JPEG string (no newlines) from Swift
 
# ─── Auth Helper ──────────────────────────────────────────────────────────────
 
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Reads the JWT from the Authorization header.
    Swift should send:  Authorization: Bearer <token>
    """
    from jose import JWTError, jwt
 
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: 'Bearer <token>'"
        )
 
    token = authorization.split(" ", 1)[1].strip()
 
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token missing subject claim")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
 
# ─── Gemini Vision Scorer ─────────────────────────────────────────────────────
 
def score_task_with_gemini(category: str, task: str, image_base64: str) -> dict:
    """
    Sends the image + task to Gemini and returns a score (0.0–1.0) + feedback string.
    Falls back gracefully if Gemini returns malformed JSON.
    """
    # Decode base64 — strip any accidental whitespace/newlines Swift may have added
    try:
        clean_b64 = image_base64.replace("\n", "").replace("\r", "").strip()
        image_bytes = base64.b64decode(clean_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")
 
    image_part = {
        "mime_type": "image/jpeg",
        "data": image_bytes
    }
 
    prompt = f"""
You are judging whether someone has completed a self-improvement task.
 
Category: {category}
Task: {task}
 
Look at the photo and decide how well they completed the task.
 
Reply ONLY with a valid JSON object in this exact format, no markdown, no extra text:
{{
  "score": <number between 0.0 and 1.0>,
  "feedback": "<one encouraging sentence about what you see>"
}}
 
Scoring guide:
- 0.9-1.0: Photo clearly and directly shows the completed task
- 0.6-0.8: Photo is related but doesn't fully prove completion
- 0.3-0.5: Photo is loosely related or unclear
- 0.0-0.2: Photo has nothing to do with the task
"""
 
    try:
        response = gemini.generate_content([prompt, image_part])
        raw = response.text.strip()
 
        # Strip markdown code fences if Gemini wraps its response anyway
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]).strip()
 
        result = json.loads(raw)
        score = max(0.0, min(1.0, float(result["score"])))
        feedback = str(result.get("feedback", "Keep building those habits!"))
        return {"score": score, "feedback": feedback}
 
    except json.JSONDecodeError:
        # Gemini response wasn't valid JSON — give a neutral score and carry on
        return {"score": 0.5, "feedback": "Task received! Keep building those habits."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")
 
# ─── Routes ───────────────────────────────────────────────────────────────────
 
@router.get("/categories")
def get_categories():
    """Returns all valid habit categories."""
    return {
        "categories": VALID_CATEGORIES,
        "total": len(VALID_CATEGORIES)
    }
 
 
@router.post("/generate")
def generate_tasks(
    request: TaskGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Given a list of categories, returns one random task per category.
    """
    invalid = [c for c in request.categories if c not in VALID_CATEGORIES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid categories: {invalid}. Valid options: {VALID_CATEGORIES}"
        )
 
    tasks = {category: random.choice(DEFAULT_TASKS[category]) for category in request.categories}
 
    return {
        "user_id": user.id,
        "tasks": tasks,
        "total": len(tasks)
    }
 
 
@router.post("/complete")
def complete_task(
    request: TaskCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Accepts a completed task + photo, scores it with Gemini,
    saves a HabitLog, and updates the user's AvatarState morph value.
    """
    # Validate category
    if request.category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{request.category}'. Valid options: {VALID_CATEGORIES}"
        )
 
    # Score the photo with Gemini
    result = score_task_with_gemini(request.category, request.task, request.image)
    score = result["score"]
    feedback = result["feedback"]
 
    # Save habit log
    habit_log = HabitLog(
        user_id=user.id,
        habit_category=request.category,
        habit_description=request.task,
        health_score=score
    )
    db.add(habit_log)
 
    # Update the avatar morph for this category
    # score 1.0 -> +0.010 | score 0.5 -> +0.005 | score 0.2 -> +0.002
    avatar = db.query(AvatarState).filter(AvatarState.user_id == user.id).first()
 
    if not avatar:
        raise HTTPException(
            status_code=404,
            detail="AvatarState not found for this user. Ensure it is created during signup."
        )
 
    morph_field = f"{request.category}_morph"
 
    if not hasattr(avatar, morph_field):
        raise HTTPException(
            status_code=400,
            detail=f"Avatar has no morph field for category '{request.category}'"
        )
 
    current_morph = getattr(avatar, morph_field)
    morph_increase = round(score * 0.01, 4)
    new_morph_value = min(round(current_morph + morph_increase, 4), 1.0)
    setattr(avatar, morph_field, new_morph_value)
 
    # Commit everything together so either both save or neither does
    db.commit()
    db.refresh(avatar)
 
    return {
        "message": "Task completed successfully",
        "category": request.category,
        "task": request.task,
        "score": score,                     # 0.0–1.0 Gemini rating
        "morph_increase": morph_increase,   # how much the avatar moved (max 0.01)
        "new_morph_value": new_morph_value, # updated avatar value for this category
        "feedback": feedback
    }
# 