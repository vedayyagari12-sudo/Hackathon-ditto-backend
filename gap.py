from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from database import get_db
from models import User, AvatarState, IdealSelf

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

    if not avatar or not ideal:
        raise HTTPException(
            status_code=400,
            detail="Complete onboarding first"
        )

    # Calculate gap for each category
    categories = {
        "sleep": (avatar.sleep_morph, ideal.target_sleep),
        "physique": (avatar.physique_morph, ideal.target_physique),
        "water": (avatar.water_morph, ideal.target_water),
        "nutrition": (avatar.nutrition_morph, ideal.target_nutrition),
        "mood": (avatar.mood_morph, ideal.target_mood),
        "school": (avatar.school_morph, ideal.target_school),
        "work": (avatar.work_morph, ideal.target_work),
        "mindfulness": (avatar.mindfulness_morph, ideal.target_mindfulness),
        "screentime": (avatar.screentime_morph, ideal.target_screentime),
        "social": (avatar.social_morph, ideal.target_social)
    }

    gaps = {}
    for category, (current, target) in categories.items():
        gap = round(target - current, 2)
        gaps[category] = {
            "current": current,
            "target": target,
            "gap": gap,
            "percentage_closed": round((current / target * 100) if target > 0 else 100, 1)
        }

    # Overall gap score
    total_gap = sum(g["gap"] for g in gaps.values())
    avg_gap = round(total_gap / len(gaps), 2)

    # Find biggest gap — what to focus on
    biggest_gap = max(gaps, key=lambda x: gaps[x]["gap"])

    return {
        "gaps": gaps,
        "overall_gap": avg_gap,
        "biggest_gap": biggest_gap,
        "focus_message": f"Focus on {biggest_gap} — it has the most room for improvement!",
        "current_clone_overall": round(sum(c for c, _ in categories.values()) / len(categories), 2),
        "ideal_clone_overall": round(sum(t for _, t in categories.values()) / len(categories), 2)
    }
