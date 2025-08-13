from fastapi import APIRouter
from app.db import ping_db

router = APIRouter()

@router.get("")
def db_check():
    ping_db()
    return {"database": "ok"}
