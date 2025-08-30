from fastapi import APIRouter, Depends, HTTPException, status, Request
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

@router.post("/token", summary="Login")
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Accepts either:
      - JSON: {"email": "...", "password": "..."} (or {"username": "...", "password": "..."})
      - Form:  username=...&password=... (application/x-www-form-urlencoded)
    Returns:  {"access_token": "...", "token_type": "bearer"}
    """
    # 1) Parse credentials from JSON or form (fallback)
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
        # Bad body payload – treat as invalid credentials
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not username or not password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # 2) Authenticate (your function should look the user up by email and bcrypt-verify)
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # 3) Issue JWT
    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}
