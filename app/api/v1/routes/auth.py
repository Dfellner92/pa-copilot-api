from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List

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

def _roles_string_to_list(roles_str: str) -> List[str]:
    # Convert comma-separated string to list
    if not roles_str or not roles_str.strip():
        return []
    return [role.strip() for role in roles_str.split(',') if role.strip()]

@router.post("/register", summary="Register new user", tags=["auth"])
async def register(user_data: UserCreateIn, db: Session = Depends(get_db)):
    """Register a new user with email, password, and roles."""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Store roles as-is (already a string from frontend)
    roles_str = user_data.roles if user_data.roles else 'clinician'
    
    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        roles=roles_str
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserOut(
            id=str(new_user.id),
            email=new_user.email,
            roles=user_data.roles  # Return as string, not list
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.post("/token", summary="Login", tags=["auth"])
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Accepts either:
      - JSON: {"email": "...", "password": "..."} (or {"username": "...", "password": "..."})
      - Form:  username=...&password=... (application/x-www-form-urlencoded)
    """
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            body = await request.json()
            email_or_username = body.get("email") or body.get("username", "")
            password = body.get("password", "")
        else:
            form = await request.form()
            email_or_username = form.get("username", "")
            password = form.get("password", "")
        
        if not email_or_username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email/username and password are required"
            )
        
        user = authenticate_user(db, email_or_username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password"
            )
        
        # Convert roles string to list for token creation
        roles_list = _roles_string_to_list(user.roles)
        
        access_token = create_access_token(
            sub=user.email, 
            roles=roles_list
        )
        
        return TokenOut(access_token=access_token, token_type="bearer")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/seed-users", summary="Seed demo users", tags=["auth"])
def seed_users(db: Session = Depends(get_db)):
    """Create demo users for testing."""
    demo_users = [
        {"email": "demo@demo.com", "password": "demo123", "roles": ["admin"]},
        {"email": "clinician@demo.com", "password": "demo123", "roles": ["clinician"]},
    ]
    
    created_users = []
    
    for user_data in demo_users:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            continue
            
        # Hash password
        hashed_password = hash_password(user_data["password"])
        
        # Convert roles list to comma-separated string
        roles_str = ','.join(user_data["roles"])
        
        # Create user
        new_user = User(
            email=user_data["email"],
            hashed_password=hashed_password,
            roles=roles_str
        )
        
        db.add(new_user)
        created_users.append({
            "email": user_data["email"],
            "roles": user_data["roles"]
        })
    
    try:
        db.commit()
        return {"message": f"Created {len(created_users)} demo users", "users": created_users}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed users: {str(e)}"
        )
