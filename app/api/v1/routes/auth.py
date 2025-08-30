from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.models import User
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()

def authenticate_user(db: Session, email_or_username: str, password: str) -> User | None:
    # We store emails; accept either "email" or "username" coming from client
    user = db.query(User).filter(User.email == email_or_username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

@router.post("/seed", summary="Create a demo user", tags=["auth"])
def seed_user(email: str, password: str, roles: str = "clinician", db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        return {"detail": "exists"}
    user = User(email=email, hashed_password=hash_password(password), roles=roles)
    db.add(user)
    db.commit()
    return {"detail": "ok"}

@router.post("/token", summary="Login", tags=["auth"])
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Accepts either:
      - JSON: {"email": "...", "password": "..."} (or {"username": "...", "password": "..."})
      - Form:  username=...&password=... (application/x-www-form-urlencoded)
    Returns:  {"access_token": "...", "token_type": "bearer"}
    """
    content_type = request.headers.get("content-type", "")
    username = ""
    password = ""

    try:
        if "application/json" in content_type:
            body = await request.json()
            username = (body.get("email") or body.get("username") or "").strip()
            password = (body.get("password") or "").strip()
        else:
            form = await request.form()
            username = (form.get("username") or form.get("email") or "").strip()
            password = (form.get("password") or "").strip()
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not username or not password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id), user.roles)
    return {"access_token": token, "token_type": "bearer"}
