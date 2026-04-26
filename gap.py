from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from database import get_db
from models import User, AvatarState, IdealSelf, AIClone
from ai_clone import grow_ai_clone

router = APIRouter(prefix="/gap", tags=["gap"])

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

@router.get("/analysis")
def get_gap_analysis(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)

    avatar = db.query(AvatarState).filter(AvatarState.user_id == user.id).first()
    ideal = db.query(IdealSelf).filter(IdealSelf.user_id == user.id).first()
    ai_clone = db.query(AIClone).filter(AIClone.user_id == user.id).first()

    if not avatar or not ideal:
        raise HTTPException(status_code=400, detail="Complete onboarding first")

    # Grow AI nemesis before comparing
    if ai_clone:
        ai_clone = grow_ai_clone(ai_clone, db)

    categories = ["sleep", "physique", "water", "nutrition", "mood",
                  "school", "work", "mindfulness", "screentime", "social"]

    you = {c: getattr(avatar, f"{c}_morph") for c in categories}
    ideal_vals = {
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
    }
    ai_vals = {c: getattr(ai_clone, f"{c}_morph") for c in categories} if ai_clone else {c: 0.2 for c in categories}

    # Gap vs ideal self
    gap_vs_ideal = {}
    for c in categories:
        gap = round(ideal_vals[c] - you[c], 2)
        gap_vs_ideal[c] = {
            "you": you[c],
            "ideal": ideal_vals[c],
            "gap": gap,
            "percentage_closed": round((you[c] / ideal_vals[c] * 100) if ideal_vals[c] > 0 else 100, 1)
        }

    # Gap vs AI nemesis
    gap_vs_ai = {}
    winning_categories = []
    losing_categories = []
    for c in categories:
        diff = round(you[c] - ai_vals[c], 2)
        gap_vs_ai[c] = {
            "you": you[c],
            "ai_nemesis": ai_vals[c],
            "difference": diff,
            "status": "winning" if diff >= 0 else "losing"
        }
        if diff >= 0:
            winning_categories.append(c)
        else:
            losing_categories.append(c)

    overall_vs_ai = round(sum(you[c] - ai_vals[c] for c in categories) / len(categories), 2)

    return {
        "you_overall": round(sum(you.values()) / len(you), 2),
        "ideal_overall": round(sum(ideal_vals.values()) / len(ideal_vals), 2),
        "ai_nemesis_overall": round(sum(ai_vals.values()) / len(ai_vals), 2),
        "gap_vs_ideal": gap_vs_ideal,
        "gap_vs_ai_nemesis": gap_vs_ai,
        "competition": {
            "status": "winning" if overall_vs_ai >= 0 else "losing",
            "overall_difference": overall_vs_ai,
            "winning_categories": winning_categories,
            "losing_categories": losing_categories,
            "message": "You are ahead of your AI nemesis!" if overall_vs_ai >= 0 else "Your AI nemesis is beating you! Complete more tasks!"
        }
    }