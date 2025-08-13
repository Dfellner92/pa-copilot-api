from fastapi import APIRouter
from .routes import requirements, db_check

api_router = APIRouter()

api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])
api_router.include_router(db_check.router,    prefix="/db-check",    tags=["ops"])
