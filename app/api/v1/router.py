from fastapi import APIRouter
from .routes import requirements, db_check, auth

api_router = APIRouter()

api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])
api_router.include_router(db_check.router,    prefix="/db-check",    tags=["ops"])
api_router.include_router(auth.router,        prefix="/auth",        tags=["auth"])
