from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os
from database import get_db
from models import User, AIClone

router = APIRouter(prefix="/ai-clone", tags=["ai-clone"])

# How much the AI nemesis grows per day per category
AI_DAILY_GROWTH = 0.03

# Max the AI nemesis can reach
AI_MAX_MORPH = 0.95

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

def grow_ai_clone(ai_clone: AIClone, db: Session):
    # Calculate how many days since last growth
    now = datetime.now(timezone.utc)
    last_grown = ai_clone.last_grown

    if last_grown.tzinfo is None:
        last_grown = last_grown.replace(tzinfo=timezone.utc)

    days_passed = (now - last_grown).days

    if days_passed < 1:
        return ai_clone

    # Grow each morph value by AI_DAILY_GROWTH per day passed
    morphs = [
        "sleep_morph", "physique_morph", "water_morph",
        "nutrition_morph", "mood_morph", "school_morph",
        "work_morph", "mindfulness_morph", "screentime_morph",
        "social_morph"
    ]

    for morph in morphs:
        current = getattr(ai_clone, morph)
        new_value = min(current + (AI_DAILY_GROWTH * days_passed), AI_MAX_MORPH)
        setattr(ai_clone, morph, round(new_value, 3))

    ai_clone.last_grown = now
    db.commit()
    return ai_clone

@router.get("/status")
def get_ai_clone_status(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)

    ai_clone = db.query(AIClone).filter(AIClone.user_id == user.id).first()
    if not ai_clone:
        raise HTTPException(status_code=404, detail="Complete onboarding first")

    # Grow the AI clone based on days passed
    ai_clone = grow_ai_clone(ai_clone, db)

    return {
        "ai_nemesis": {
            "sleep": ai_clone.sleep_morph,
            "physique": ai_clone.physique_morph,
            "water": ai_clone.water_morph,
            "nutrition": ai_clone.nutrition_morph,
            "mood": ai_clone.mood_morph,
            "school": ai_clone.school_morph,
            "work": ai_clone.work_morph,
            "mindfulness": ai_clone.mindfulness_morph,
            "screentime": ai_clone.screentime_morph,
            "social": ai_clone.social_morph
        },
        "last_grown": ai_clone.last_grown.strftime("%Y-%m-%d"),
        "daily_growth_rate": AI_DAILY_GROWTH,
        "message": "Your AI nemesis is getting stronger every day. Keep up!"
    }