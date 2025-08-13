from fastapi import APIRouter, Query, Depends
from app.api.v1.deps import require_role
from app.services.requirements import check_requirements
from app.domain.schemas import RequirementsOut

router = APIRouter()

@router.get("", response_model=RequirementsOut)
def get_requirements(
    code: str = Query(..., description="CPT/HCPCS code"),
    _: None = Depends(require_role("clinician")),  
    ):
    requires, docs = check_requirements(code)
    return {"requiresAuth": requires, "requiredDocs": docs}