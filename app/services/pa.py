from sqlalchemy.orm import Session
from app.services.requirements import check_requirements
from app.domain.models import PriorAuthRequest, PriorAuthStatus

def decide_initial_status(code: str, requires: bool) -> tuple[PriorAuthStatus, str]:
    """
    Simple demo policy:
      - if not requires → not_required / ""
      - code 70551 → approved
      - code 70553 → pending (need neurology consult)
      - otherwise → pending (manual review)
    """
    if not requires:
        return PriorAuthStatus.not_required, ""
    if code == "70551":
        return PriorAuthStatus.approved, "Approved per policy"
    if code == "70553":
        return PriorAuthStatus.pending, "More information required: neurology consult"
    return PriorAuthStatus.pending, "Queued for clinical review"

def create_pa(db: Session, *, patient_id: str, coverage_id: str, code: str, diagnosis_codes: list[str]) -> PriorAuthRequest:
    requires, required_docs = check_requirements(code)
    status, disposition = decide_initial_status(code, requires)

    par = PriorAuthRequest(
        patient_id=patient_id,
        coverage_id=coverage_id,
        code=code,
        diagnosis_codes=",".join(diagnosis_codes),
        status=status,
        disposition=disposition,
    )
    db.add(par)
    db.commit()
    db.refresh(par)

    # Return object plus computed fields for the API layer to include
    par._requires = requires             # attach transient attrs for convenience
    par._required_docs = required_docs
    return par
