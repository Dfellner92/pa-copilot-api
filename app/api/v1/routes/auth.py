from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.models import User
from app.domain.schemas import UserCreateIn, UserOut, UserLoginIn, TokenOut
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

def _roles_string_to_list(roles_str: str) -> list[str]:
    """Convert comma-separated roles string to list"""
    if not roles_str:
        return []
    return [role.strip() for role in roles_str.split(",") if role.strip()]

def _roles_list_to_string(roles_list: list[str]) -> str:
    """Convert roles list to comma-separated string"""
    return ",".join(roles_list)

@router.post("/register", response_model=UserOut, summary="Register a new user", tags=["auth"])
def register_user(user_data: UserCreateIn, db: Session = Depends(get_db)):
    """Register a new user with email, password, and roles"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate roles
    valid_roles = ["clinician", "admin", "reviewer"]
    user_roles = _roles_string_to_list(user_data.roles)
    invalid_roles = [role for role in user_roles if role not in valid_roles]
    if invalid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid roles: {', '.join(invalid_roles)}. Valid roles: {', '.join(valid_roles)}")
    
    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        roles=user_data.roles
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserOut(id=str(user.id), email=user.email, roles=user.roles)

@router.post("/seed", summary="Create a demo user", tags=["auth"])
def seed_user(email: str, password: str, roles: str = "clinician", db: Session = Depends(get_db)):
    """Legacy endpoint for seeding demo users"""
    if db.query(User).filter(User.email == email).first():
        return {"detail": "exists"}
    user = User(email=email, hashed_password=hash_password(password), roles=roles)
    db.add(user)
    db.commit()
    return {"detail": "ok"}

@router.post("/token", response_model=TokenOut, summary="Login", tags=["auth"])
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

    # Convert string roles to list for token creation
    roles_list = _roles_string_to_list(user.roles)
    
    token = create_access_token(str(user.id), roles_list)
    return TokenOut(access_token=token, token_type="bearer")

@router.get("/users", response_model=List[UserOut], summary="List all users", tags=["auth"])
def list_users(db: Session = Depends(get_db)):
    """List all users (for admin purposes)"""
    users = db.query(User).all()
    return [UserOut(id=str(user.id), email=user.email, roles=user.roles) for user in users]
