from fastapi import APIRouter
from .routes import requirements, db_check, auth, prior_auth, attachments, patients

api_router = APIRouter()

api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])
api_router.include_router(db_check.router,    prefix="/db-check",    tags=["ops"])
api_router.include_router(auth.router,        prefix="/auth",        tags=["auth"])
api_router.include_router(prior_auth.router,  prefix="/prior-auth",  tags=["prior-auth"])
api_router.include_router(attachments.router, prefix="/attachments", tags=["attachments"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])