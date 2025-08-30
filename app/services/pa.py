# app/services/pa.py
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from app.services.requirements import check_requirements
from app.domain.models import (
    Patient,
    Coverage,
    PriorAuthRequest,
    PriorAuthStatus,
)

# -------- helpers

def _to_uuid(v):
    return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))

def _maybe_uuid(v):
    try:
        return _to_uuid(v)
    except Exception:
        return None

def _resolve_patient_id(db: Session, ident: str | uuid.UUID) -> uuid.UUID:
    """
    Accepts a UUID or an external identifier (e.g. MRN).
    Tries UUID first; otherwise looks up Patient.external_id.
    """
    u = _maybe_uuid(ident)
    if u:
        return u

    row = (
        db.query(Patient)
        .filter(Patient.external_id == str(ident))
        .first()
    )
    if not row:
        raise NoResultFound(f"Patient not found for identifier '{ident}'")
    return row.id

def _resolve_coverage_id(db: Session, ident: str | uuid.UUID) -> uuid.UUID:
    """
    Accepts a UUID or an external identifier.
    Tries UUID first; otherwise looks up Coverage.external_id,
    and finally falls back to member_id for backward compatibility.
    """
    u = _maybe_uuid(ident)
    if u:
        return u

    row = (
        db.query(Coverage)
        .filter(Coverage.external_id == str(ident))
        .first()
    )
    if not row:
        row = (
            db.query(Coverage)
            .filter(Coverage.member_id == str(ident))
            .first()
        )
    if not row:
        raise NoResultFound(f"Coverage not found for identifier '{ident}'")
    return row.id

def _decide_initial_status(requires: bool) -> tuple[PriorAuthStatus, str]:
    """
    Pure dynamic logic — no code-specific rules.
    """
    if not requires:
        return PriorAuthStatus.not_required, "No prior authorization required"
    return PriorAuthStatus.pending, "Submitted for review"

# -------- main entrypoint

def create_pa(
    db: Session,
    *,
    patient_id: str | uuid.UUID,
    coverage_id: str | uuid.UUID,
    code: str,
    diagnosis_codes: list[str],
) -> PriorAuthRequest:
    # Resolve external identifiers/UUIDs
    pid = _resolve_patient_id(db, patient_id)
    cid = _resolve_coverage_id(db, coverage_id)

    # Dynamic requirements engine decides whether PA is required
    requires, required_docs = check_requirements(code)

    status, disposition = _decide_initial_status(requires)

    par = PriorAuthRequest(
        patient_id=pid,
        coverage_id=cid,
        code=code,
        diagnosis_codes=",".join(diagnosis_codes or []),
        status=status,
        disposition=disposition,
    )
    db.add(par)
    db.commit()
    db.refresh(par)

    # non-persisted convenience fields for the response layer
    par._requires = requires
    par._required_docs = required_docs
    return par
