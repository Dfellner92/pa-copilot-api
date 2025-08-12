from pydantic import BaseModel
from typing import List

class RequirementsOut(BaseModel):
    requiresAuth: bool
    requiredDocs: List[str]