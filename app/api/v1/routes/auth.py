from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db import get_db
from app.domain.models import User
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()

@router.post("/seed", summary="Create a demo user")
def seed_user(email: str, password: str, roles: str = "clinician", db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        return {"detail": "exists"}
    user = User(email=email, hashed_password=hash_password(password), roles=roles)
    db.add(user)
    db.commit()
    return {"detail": "ok"}

@router.post("/token", summary="Login to get access token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    roles = [r for r in user.roles.split(",") if r]
    token = create_access_token(sub=str(user.id), roles=roles)
    return {"access_token": token, "token_type": "bearer"}
