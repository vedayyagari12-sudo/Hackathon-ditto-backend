from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    habit_logs = relationship("HabitLog", back_populates="user")
    avatar_state = relationship("AvatarState", back_populates="user", uselist=False)
    ideal_self = relationship("IdealSelf", back_populates="user", uselist=False)
    ai_clone = relationship("AIClone", back_populates="user", uselist=False)


class HabitLog(Base):
    __tablename__ = "habit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime(timezone=True), server_default=func.now())
    habit_description = Column(String)
    habit_category = Column(String)
    health_score = Column(Float, default=0.0)
    
    user = relationship("User", back_populates="habit_logs")


class AvatarState(Base):
    __tablename__ = "avatar_states"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    sleep_morph = Column(Float, default=0.0)
    physique_morph = Column(Float, default=0.0)
    water_morph = Column(Float, default=0.0)
    nutrition_morph = Column(Float, default=0.0)
    mood_morph = Column(Float, default=0.0)
    school_morph = Column(Float, default=0.0)
    work_morph = Column(Float, default=0.0)
    mindfulness_morph = Column(Float, default=0.0)
    screentime_morph = Column(Float, default=0.0)
    social_morph = Column(Float, default=0.0)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user = relationship("User", back_populates="avatar_state")


class IdealSelf(Base):
    __tablename__ = "ideal_selves"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    target_sleep = Column(Float, default=1.0)
    target_physique = Column(Float, default=1.0)
    target_water = Column(Float, default=1.0)
    target_nutrition = Column(Float, default=1.0)
    target_mood = Column(Float, default=1.0)
    target_school = Column(Float, default=1.0)
    target_work = Column(Float, default=1.0)
    target_mindfulness = Column(Float, default=1.0)
    target_screentime = Column(Float, default=1.0)
    target_social = Column(Float, default=1.0)
    
    user = relationship("User", back_populates="ideal_self")


class AIClone(Base):
    __tablename__ = "ai_clones"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # AI Nemesis morph values — grows automatically over time
    sleep_morph = Column(Float, default=0.2)
    physique_morph = Column(Float, default=0.2)
    water_morph = Column(Float, default=0.2)
    nutrition_morph = Column(Float, default=0.2)
    mood_morph = Column(Float, default=0.2)
    school_morph = Column(Float, default=0.2)
    work_morph = Column(Float, default=0.2)
    mindfulness_morph = Column(Float, default=0.2)
    screentime_morph = Column(Float, default=0.2)
    social_morph = Column(Float, default=0.2)
    
    last_grown = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="ai_clone")