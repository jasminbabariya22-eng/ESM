from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.schemas.user import UserResponse
from typing import List

app = FastAPI()
app.include_router(auth_router)
app.include_router(user_router)

@app.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).limit(5).all()