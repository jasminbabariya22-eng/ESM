from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.api.auth import router as auth_router

app = FastAPI()
app.include_router(auth_router)

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).limit(5).all()
    return users