from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import os
from database import get_db
from models import User, AvatarState, IdealSelf, AIClone

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

VALID_CATEGORIES = [
    "sleep", "physique", "water", "nutrition", "mood",
    "school", "work", "mindfulness", "screentime", "social"
]

DEFAULT_CURRENT = {
    "sleep": 0.4,
    "physique": 0.4,
    "water": 0.4,
    "nutrition": 0.4,
    "mood": 0.5,
    "school": 0.4,
    "work": 0.4,
    "mindfulness": 0.4,
    "screentime": 0.4,
    "social": 0.4
}

class OnboardingRequest(BaseModel):
    categories: List[str]
    current_description: str
    goal_description: str

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

def score_description_with_ai(description: str, categories: List[str], is_goal: bool):
    scores = {}
    for category in categories:
        if is_goal:
            scores[category] = 1.0
        else:
            scores[category] = DEFAULT_CURRENT[category]
    return scores

@router.post("/setup")
def setup_onboarding(
    request: OnboardingRequest,
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)

    invalid = [c for c in request.categories if c not in VALID_CATEGORIES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid categories: {invalid}")

    current_scores = score_description_with_ai(
        request.current_description, request.categories, is_goal=False
    )
    goal_scores = score_description_with_ai(
        request.goal_description, request.categories, is_goal=True
    )

    # Create or update your avatar (you)
    avatar = db.query(AvatarState).filter(AvatarState.user_id == user.id).first()
    if not avatar:
        avatar = AvatarState(user_id=user.id)
        db.add(avatar)
    for category in request.categories:
        setattr(avatar, f"{category}_morph", current_scores[category])

    # Create or update ideal self
    ideal = db.query(IdealSelf).filter(IdealSelf.user_id == user.id).first()
    if not ideal:
        ideal = IdealSelf(user_id=user.id)
        db.add(ideal)
    for category in request.categories:
        setattr(ideal, f"target_{category}", goal_scores[category])

    # Create or update AI nemesis — starts at 0.2 same as user
    ai_clone = db.query(AIClone).filter(AIClone.user_id == user.id).first()
    if not ai_clone:
        ai_clone = AIClone(user_id=user.id)
        db.add(ai_clone)
    for category in request.categories:
        setattr(ai_clone, f"{category}_morph", current_scores[category])

    db.commit()

    return {
        "message": "Onboarding complete! Your three clones have been created.",
        "selected_categories": request.categories,
        "you": current_scores,
        "ideal_self": goal_scores,
        "ai_nemesis": {category: 0.2 for category in request.categories},
        "gap_vs_ideal": {
            category: round(goal_scores[category] - current_scores[category], 2)
            for category in request.categories
        }
    }

@router.get("/status")
def get_onboarding_status(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)

    avatar = db.query(AvatarState).filter(AvatarState.user_id == user.id).first()
    ideal = db.query(IdealSelf).filter(IdealSelf.user_id == user.id).first()
    ai_clone = db.query(AIClone).filter(AIClone.user_id == user.id).first()

    if not avatar or not ideal:
        return {"onboarded": False, "message": "User has not completed onboarding"}

    return {
        "onboarded": True,
        "you": {
            "sleep": avatar.sleep_morph,
            "physique": avatar.physique_morph,
            "water": avatar.water_morph,
            "nutrition": avatar.nutrition_morph,
            "mood": avatar.mood_morph,
            "school": avatar.school_morph,
            "work": avatar.work_morph,
            "mindfulness": avatar.mindfulness_morph,
            "screentime": avatar.screentime_morph,
            "social": avatar.social_morph
        },
        "ideal_self": {
            "sleep": ideal.target_sleep,
            "physique": ideal.target_physique,
            "water": ideal.target_water,
            "nutrition": ideal.target_nutrition,
            "mood": ideal.target_mood,
            "school": ideal.target_school,
            "work": ideal.target_work,
            "mindfulness": ideal.target_mindfulness,
            "screentime": ideal.target_screentime,
            "social": ideal.target_social
        },
        "ai_nemesis": {
            "sleep": ai_clone.sleep_morph if ai_clone else 0.2,
            "physique": ai_clone.physique_morph if ai_clone else 0.2,
            "water": ai_clone.water_morph if ai_clone else 0.2,
            "nutrition": ai_clone.nutrition_morph if ai_clone else 0.2,
            "mood": ai_clone.mood_morph if ai_clone else 0.2,
            "school": ai_clone.school_morph if ai_clone else 0.2,
            "work": ai_clone.work_morph if ai_clone else 0.2,
            "mindfulness": ai_clone.mindfulness_morph if ai_clone else 0.2,
            "screentime": ai_clone.screentime_morph if ai_clone else 0.2,
            "social": ai_clone.social_morph if ai_clone else 0.2
        }
    }