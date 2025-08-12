from fastapi import APIRouter
from .routes import requirements

api_router = APIRouter()

api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])