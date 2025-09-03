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

# Patient creation schema
class PatientCreateIn(BaseModel):
    external_id: str
    first_name: str
    last_name: str
    birth_date: str

# NEW: Coverage creation schema
class CoverageCreateIn(BaseModel):
    external_id: str
    member_id: str
    plan: str
    payer: str
    patient_id: str

# dev only
class DocumentRefOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    url: str