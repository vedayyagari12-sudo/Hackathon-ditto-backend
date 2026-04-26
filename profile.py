from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta
import os
import random
from database import get_db
from models import User, AvatarState, IdealSelf, HabitLog

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

    # Get avatar state
    avatar = db.query(AvatarState).filter(AvatarState.user_id == user.id).first()
    ideal = db.query(IdealSelf).filter(IdealSelf.user_id == user.id).first()

    # Get streak
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

    # Get today's habit count
    today_logs = db.query(HabitLog).filter(
        HabitLog.user_id == user.id,
        func.date(HabitLog.date) == date.today()
    ).count()

    # Build current and ideal clone data
    current_clone = None
    ideal_clone = None
    gap = None

    if avatar:
        current_clone = {
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

    if current_clone and ideal_clone:
        gaps = {
            cat: round(ideal_clone[cat] - current_clone[cat], 2)
            for cat in current_clone
        }
        biggest_gap = max(gaps, key=lambda x: gaps[x])
        gap = {
            "by_category": gaps,
            "overall": round(sum(gaps.values()) / len(gaps), 2),
            "biggest_gap": biggest_gap
        }

    # Generate today's tasks for categories user has set up
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
        "current_clone": current_clone,
        "ideal_clone": ideal_clone,
        "gap": gap,
        "todays_tasks": todays_tasks,
        "onboarded": avatar is not None and ideal is not None
    }