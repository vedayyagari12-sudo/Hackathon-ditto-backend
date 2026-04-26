from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
import os
from database import get_db
from models import User, HabitLog

router = APIRouter(prefix="/streak", tags=["streak"])

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

def calculate_streak(user_id: int, db: Session):
    # Get all dates the user logged a habit, most recent first
    logs = db.query(
        func.date(HabitLog.date).label("log_date")
    ).filter(
        HabitLog.user_id == user_id
    ).distinct().order_by(
        func.date(HabitLog.date).desc()
    ).all()

    if not logs:
        return 0

    streak = 0
    today = date.today()
    check_date = today

    for log in logs:
        log_date = log.log_date
        # Handle both string and date objects
        if isinstance(log_date, str):
            log_date = datetime.strptime(log_date, "%Y-%m-%d").date()

        if log_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif log_date == check_date - timedelta(days=1):
            # Allow today to be missed if yesterday was logged
            check_date = log_date
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return streak

@router.get("/status")
def get_streak(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)
    streak = calculate_streak(user.id, db)

    # Get total habits logged
    total_logs = db.query(HabitLog).filter(
        HabitLog.user_id == user.id
    ).count()

    # Get today's logs
    today_logs = db.query(HabitLog).filter(
        HabitLog.user_id == user.id,
        func.date(HabitLog.date) == date.today()
    ).count()

    return {
        "streak": streak,
        "total_habits_logged": total_logs,
        "habits_logged_today": today_logs,
        "message": f"You are on a {streak} day streak!" if streak > 0 else "Log a habit today to start your streak!"
    }

@router.get("/history")
def get_history(
    token: str,
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)

    # Get last 7 days of habit logs
    seven_days_ago = datetime.now() - timedelta(days=7)
    logs = db.query(HabitLog).filter(
        HabitLog.user_id == user.id,
        HabitLog.date >= seven_days_ago
    ).order_by(HabitLog.date.desc()).all()

    return {
        "last_7_days": [
            {
                "date": log.date.strftime("%Y-%m-%d"),
                "category": log.habit_category,
                "score": log.health_score,
                "description": log.habit_description
            }
            for log in logs
        ],
        "total": len(logs)
    }