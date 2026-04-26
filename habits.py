from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os
import json
from google import genai
from database import get_db
from models import User, HabitLog, AvatarState

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

router = APIRouter(prefix="/habits", tags=["habits"])

HABIT_SCORER_PROMPT = """You are a health and wellness scoring system for an app called Ditto.
Your job is to score a user's logged habit and return how healthy it is.

The 10 habit categories are:
- sleep, physique, water, nutrition, mood, school, work, mindfulness, screentime, social

You must return ONLY a JSON object with exactly these fields:
{
  "category": "the category name",
  "score": 0.0,
  "feedback": "one short encouraging sentence"
}

Rules:
- score must be between 0.0 (terrible) and 1.0 (perfect)
- Be strict but fair
- Consider context and effort
- Never return anything except the JSON object
"""

class HabitRequest(BaseModel):
    category: str
    description: str

def get_current_user(token: str, db: Session):
    from jose import JWTError, jwt
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def score_habit_with_ai(category: str, description: str):
    prompt = f"{HABIT_SCORER_PROMPT}\n\nCategory: {category}\nDescription: {description}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

@router.post("/log")
def log_habit(
    request: HabitRequest,
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)
    result = score_habit_with_ai(request.category, request.description)

    habit_log = HabitLog(
        user_id=user.id,
        habit_category=result["category"],
        habit_description=request.description,
        health_score=result["score"]
    )
    db.add(habit_log)

    avatar = db.query(AvatarState).filter(AvatarState.user_id == user.id).first()
    if not avatar:
        avatar = AvatarState(user_id=user.id)
        db.add(avatar)

    morph_map = {
        "sleep": "sleep_morph",
        "physique": "physique_morph",
        "water": "water_morph",
        "nutrition": "nutrition_morph",
        "mood": "mood_morph",
        "school": "school_morph",
        "work": "work_morph",
        "mindfulness": "mindfulness_morph",
        "screentime": "screentime_morph",
        "social": "social_morph"
    }

    morph_field = morph_map.get(result["category"])
    if morph_field:
        setattr(avatar, morph_field, result["score"])

    db.commit()

    return {
        "message": "Habit logged successfully",
        "category": result["category"],
        "score": result["score"],
        "feedback": result["feedback"],
        "avatar_updated": morph_field
    }
