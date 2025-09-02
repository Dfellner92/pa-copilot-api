from pydantic import BaseModel
from typing import List
from app.domain.enums import PriorAuthStatus

class RequirementsOut(BaseModel):
    requiresAuth: bool
    requiredDocs: List[str]

class PriorAuthCreateIn(BaseModel):
    patient_id: Union[str, UUID] = Field(..., description="UUID of the patient or string that can be UUID-cast")
    coverage_id: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    diagnosis_codes: List[str] = Field(default_factory=list)
    documents: List[str] = []  # names/ids (future DocumentReference)

class PriorAuthOut(BaseModel):
    id: str
    status: PriorAuthStatus
    disposition: str
    requiresAuth: bool
    requiredDocs: List[str]


# dev only
class DocumentRefOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    url: str