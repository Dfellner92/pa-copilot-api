from pydantic import BaseModel
from typing import List
from app.domain.enums import PriorAuthStatus

class RequirementsOut(BaseModel):
    requiresAuth: bool
    requiredDocs: List[str]

class PriorAuthCreateIn(BaseModel):
    patient_id: str
    coverage_id: str
    code: str
    diagnosis_codes: List[str] = []
    documents: List[str] = []  # names/ids (future DocumentReference)

class PriorAuthOut(BaseModel):
    id: str
    status: PriorAuthStatus
    disposition: str
    requiresAuth: bool
    requiredDocs: List[str]
