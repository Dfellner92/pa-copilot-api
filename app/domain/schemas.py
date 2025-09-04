from pydantic import BaseModel, EmailStr
from typing import List, Optional
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
    # Provider fields
    provider_name: Optional[str] = None
    provider_npi: Optional[str] = None

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

# Coverage creation schema
class CoverageCreateIn(BaseModel):
    external_id: str
    member_id: str
    plan: str
    payer: str
    patient_id: str

# NEW: User management schemas
class UserCreateIn(BaseModel):
    email: EmailStr
    password: str
    roles: str = "clinician"  # Comma-separated roles

class UserOut(BaseModel):
    id: str
    email: str
    roles: str

class UserLoginIn(BaseModel):
    email: str
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

# dev only
class DocumentRefOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    url: str