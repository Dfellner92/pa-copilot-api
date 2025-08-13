from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

def get_current_user_roles(token: str = Depends(oauth2_scheme)) -> list[str]:
    try:
        payload = decode_token(token)
        return payload.get("roles", [])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(role: str):
    def checker(roles: list[str] = Depends(get_current_user_roles)):
        if role not in roles and "admin" not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
    return checker
