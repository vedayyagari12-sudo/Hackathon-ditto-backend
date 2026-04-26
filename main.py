from fastapi import FastAPI
from database import engine, Base
import models
from auth import router as auth_router
from habits import router as habits_router
from tasks import router as tasks_router
from onboarding import router as onboarding_router
from streak import router as streak_router
from gap import router as gap_router
from profile import router as profile_router
from ai_clone import router as ai_clone_router



app = FastAPI(title="Ditto API")

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(habits_router)
app.include_router(tasks_router)
app.include_router(onboarding_router)
app.include_router(streak_router)
app.include_router(gap_router)
app.include_router(profile_router)
app.include_router(ai_clone_router)

@app.get("/")
def root():
    return {"status": "Ditto API is running"}