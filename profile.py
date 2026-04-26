from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta, timezone
import os
import random
from database import get_db
from models import User, AvatarState, IdealSelf, HabitLog, AIClone
from ai_clone import grow_ai_clone

router = APIRouter(prefix="/profile", tags=["profile"])

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

DEFAULT_TASKS = {
    "sleep": ["Take a photo of your bed made in the morning", "Take a photo of your phone on do not disturb before 11pm"],
    "physique": ["Take a photo of yourself at the gym or working out", "Take a photo of yourself on a walk or run outside"],
    "water": ["Take a photo of your water bottle filled up", "Take a photo of 8 empty glasses or a full water jug"],
    "nutrition": ["Take a photo of your healthy meal", "Take a photo of your plate with vegetables on it"],
    "mood": ["Take a photo of your journal with 3 things you are grateful for", "Take a photo of yourself smiling"],
    "school": ["Take a photo of your completed homework", "Take a photo of your notes from studying"],
    "work": ["Take a photo of your completed to do list", "Take a photo of your clean and organised desk"],
    "mindfulness": ["Take a photo of your meditation app showing a completed session", "Take a photo of yourself outside in nature"],
    "screentime": ["Take a photo of your screen time showing reduced usage", "Take a photo of your phone face down during a meal"],
    "social": ["Take a photo of a meal or activity with friends or family", "Take a photo of yourself and a friend or family member together"]
}

@router.get("/")
def get_profile(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)

    avatar = db.query(AvatarState).filter(AvatarState.user_id == user.id).first()
    ideal = db.query(IdealSelf).filter(IdealSelf.user_id == user.id).first()
    ai_clone = db.query(AIClone).filter(AIClone.user_id == user.id).first()

    # Grow AI nemesis
    if ai_clone:
        ai_clone = grow_ai_clone(ai_clone, db)

    # Calculate streak
    logs = db.query(
        func.date(HabitLog.date).label("log_date")
    ).filter(
        HabitLog.user_id == user.id
    ).distinct().order_by(
        func.date(HabitLog.date).desc()
    ).all()

    streak = 0
    check_date = date.today()
    for log in logs:
        log_date = log.log_date
        if isinstance(log_date, str):
            log_date = datetime.strptime(log_date, "%Y-%m-%d").date()
        if log_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    today_logs = db.query(HabitLog).filter(
        HabitLog.user_id == user.id,
        func.date(HabitLog.date) == date.today()
    ).count()

    # Build all 3 clone data
    you = None
    ideal_clone = None
    ai_nemesis = None

    if avatar:
        you = {
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
        }

    if ideal:
        ideal_clone = {
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

    if ai_clone:
        ai_nemesis = {
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
        }

    # Competition status vs AI nemesis
    competition = None
    if you and ai_nemesis:
        you_avg = sum(you.values()) / len(you)
        ai_avg = sum(ai_nemesis.values()) / len(ai_nemesis)
        competition = {
            "status": "winning" if you_avg >= ai_avg else "losing",
            "you_average": round(you_avg, 2),
            "ai_average": round(ai_avg, 2),
            "message": "You are ahead of your AI nemesis!" if you_avg >= ai_avg else "Your AI nemesis is beating you!"
        }

    # Gap vs ideal self
    gap_vs_ideal = None
    if you and ideal_clone:
        gaps = {
            cat: round(ideal_clone[cat] - you[cat], 2)
            for cat in you
        }
        biggest_gap = max(gaps, key=lambda x: gaps[x])
        gap_vs_ideal = {
            "by_category": gaps,
            "overall": round(sum(gaps.values()) / len(gaps), 2),
            "biggest_gap": biggest_gap,
            "focus_message": f"Focus on {biggest_gap} to get closer to your ideal self!"
        }

    todays_tasks = {}
    if avatar:
        for category in DEFAULT_TASKS:
            todays_tasks[category] = random.choice(DEFAULT_TASKS[category])

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "member_since": user.created_at.strftime("%Y-%m-%d")
        },
        "streak": {
            "days": streak,
            "habits_today": today_logs,
            "message": f"{streak} day streak!" if streak > 0 else "Log a habit to start your streak!"
        },
        "you": you,
        "ideal_self": ideal_clone,
        "ai_nemesis": ai_nemesis,
        "competition": competition,
        "gap_vs_ideal": gap_vs_ideal,
        "todays_tasks": todays_tasks,
        "onboarded": avatar is not None and ideal is not None
    }


# 