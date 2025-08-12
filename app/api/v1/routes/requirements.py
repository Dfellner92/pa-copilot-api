from fastapi import APIRouter, Query
from app.services.requirements import check_requirements
from app.domain.schemas import RequirementsOut

router = APIRouter()

@router.get("", response_model=RequirementsOut)
def get_requirements(code: str = Query(..., description="CPT/HCPCS code")):
    requires, docs = check_requirements(code)
    return {"requiresAuth": requires, "requiredDocs": docs}