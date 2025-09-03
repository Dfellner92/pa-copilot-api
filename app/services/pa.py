# app/services/pa.py
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from fastapi import HTTPException, status

from app.services.requirements import check_requirements
from app.domain.models import (
    Patient,
    Coverage,
    PriorAuthRequest,
    PriorAuthStatus,  # re-exported from app.domain.enums via models
)

# -----------------------
# Helpers
# -----------------------

def _to_uuid(v) -> uuid.UUID:
    return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))

def _maybe_uuid(v) -> Optional[uuid.UUID]:
    try:
        return _to_uuid(v)
    except Exception:
        return None

def _resolve_patient_id(db: Session, ident: str | uuid.UUID) -> uuid.UUID:
    """
    Accepts a UUID or Patient.external_id. Ensures the row exists either way.
    """
    u = _maybe_uuid(ident)
    if u:
        row = db.get(Patient, u)  # validate existence for UUID path
        if not row:
            raise HTTPException(status_code=404, detail=f"Patient not found: {ident}")
        return row.id

    row = db.query(Patient).filter(Patient.external_id == str(ident)).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Patient not found: {ident}")
    return row.id

def _resolve_coverage_id(db: Session, ident: str | uuid.UUID) -> uuid.UUID:
    """
    Accepts a UUID or Coverage.external_id (fallback to member_id).
    Ensures the row exists either way.
    """
    u = _maybe_uuid(ident)
    if u:
        row = db.get(Coverage, u)  # validate existence for UUID path
        if not row:
            raise HTTPException(status_code=404, detail=f"Coverage not found: {ident}")
        return row.id

    row = db.query(Coverage).filter(Coverage.external_id == str(ident)).first()
    if not row:
        row = db.query(Coverage).filter(Coverage.member_id == str(ident)).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Coverage not found: {ident}")
    return row.id

def _decide_initial_status(requires: bool) -> tuple[PriorAuthStatus, str]:
    if not requires:
        return PriorAuthStatus.not_required, "No prior authorization required"
    return PriorAuthStatus.pending, "Submitted for review"

# -----------------------
# Main entrypoint
# -----------------------

def create_pa(
    db: Session,
    *,
    patient_id: str | uuid.UUID,
    coverage_id: str | uuid.UUID,
    code: str,
    diagnosis_codes: list[str],
    provider_name: Optional[str] = None,
    provider_npi: Optional[str] = None,
) -> PriorAuthRequest:
    """
    Creates a PriorAuthRequest from either UUIDs or business identifiers.
    Returns 404 for missing patient/coverage, and 422 for integrity issues.
    """
    pid = _resolve_patient_id(db, patient_id)
    cid = _resolve_coverage_id(db, coverage_id)

    requires, required_docs = check_requirements(code)
    status_val, disposition = _decide_initial_status(requires)

    par = PriorAuthRequest(
        patient_id=pid,
        coverage_id=cid,
        code=code,
        diagnosis_codes=",".join(diagnosis_codes or []),
        status=status_val,
        disposition=disposition,
        provider_name=provider_name or "",
        provider_npi=provider_npi or "",
    )

    db.add(par)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Surface as a client error, not a 500
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not create prior auth: {str(e.orig) if getattr(e, 'orig', None) else str(e)}",
        )
    db.refresh(par)

    # Convenience fields (not persisted)
    par._requires = requires
    par._required_docs = required_docs
    return par
