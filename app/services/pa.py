# app/services/pa.py
import uuid
from typing import Iterable, Sequence
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.services.requirements import check_requirements
from app.domain.models import (
    PriorAuthRequest,
    PriorAuthStatus,
    Patient,     # expects: id(UUID), external_id(str)
    Coverage,    # expects: id(UUID), external_id(str)
    # Optional rule model (see _apply_policy_rule below)
    # PolicyRule,
)

# --------- identifier resolution (UUID or external id) ---------

def _try_uuid(v) -> uuid.UUID | None:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(str(v))
    except Exception:
        return None

def _resolve_patient_id(db: Session, ident: str | uuid.UUID) -> uuid.UUID:
    uid = _try_uuid(ident)
    if uid:
        row = db.get(Patient, uid)
        if row:
            return row.id
    row = db.query(Patient).filter(Patient.external_id == str(ident)).first()
    if row:
        return row.id
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unknown patient identifier: {ident!r} (must be UUID or known external_id)",
    )

def _resolve_coverage_id(db: Session, ident: str | uuid.UUID) -> uuid.UUID:
    uid = _try_uuid(ident)
    if uid:
        row = db.get(Coverage, uid)
        if row:
            return row.id
    row = db.query(Coverage).filter(Coverage.external_id == str(ident)).first()
    if row:
        return row.id
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unknown coverage identifier: {ident!r} (must be UUID or known external_id)",
    )

# --------- policy hook (data-driven, no hardcoded codes) ---------

def _apply_policy_rule(
    db: Session,
    *,
    code: str,
    coverage_id: uuid.UUID | None,
) -> tuple[PriorAuthStatus, str] | None:
    """
    Optional DB-backed rule that can auto-approve/deny.
    Implement a model like:

        class PolicyRule(Base):
            __tablename__ = "policy_rules"
            id: UUID PK
            code: str
            coverage_id: UUID | None
            auto_approve: bool
            auto_deny: bool
            disposition: str | None

    This function returns (status, disposition) if a matching rule is found,
    otherwise None (fall through to default logic).
    """
    try:
        from app.domain.models import PolicyRule  # import here so code runs even if model isn't present

        q = db.query(PolicyRule).filter(PolicyRule.code == code)
        if coverage_id is not None and hasattr(PolicyRule, "coverage_id"):
            q = q.filter(PolicyRule.coverage_id == coverage_id)
        rule = q.first()
        if not rule:
            return None

        disp = (getattr(rule, "disposition", None) or "").strip()

        if getattr(rule, "auto_approve", False):
            return PriorAuthStatus.approved, (disp or "Approved per policy")

        if getattr(rule, "auto_deny", False):
            # If you support a denied status in your enum, use it; otherwise pending with disposition.
            if hasattr(PriorAuthStatus, "denied"):
                return PriorAuthStatus.denied, (disp or "Denied per policy")
            return PriorAuthStatus.pending, (disp or "Requires clinical review")

        # A rule exists but doesn’t auto-approve/deny; let default logic handle.
        return None
    except Exception:
        # No PolicyRule model/table yet or query failed → ignore and use fallback logic.
        return None

# --------- default status logic (dynamic, no hardcoding) ---------

def decide_initial_status(
    db: Session,
    *,
    code: str,
    requires: bool,
    coverage_id: uuid.UUID | None,
) -> tuple[PriorAuthStatus, str]:
    # If no prior auth is required, immediately mark not_required.
    if not requires:
        return PriorAuthStatus.not_required, ""

    # Try data-driven policy (DB rule / rules engine). Returns status if a rule says so.
    rule_result = _apply_policy_rule(db, code=code, coverage_id=coverage_id)
    if rule_result:
        return rule_result

    # Fallback: requires PA but no rule ⇒ queue for review.
    return PriorAuthStatus.pending, "Queued for clinical review"

# --------- small helpers ---------

def _csv(values: Sequence[str] | Iterable[str] | None) -> str:
    if not values:
        return ""
    return ",".join([str(v).strip() for v in values if str(v).strip()])

# --------- main entry point ---------

def create_pa(
    db: Session,
    *,
    patient_id: str,          # UUID or external id
    coverage_id: str,         # UUID or external id
    code: str,
    diagnosis_codes: list[str] | None,
) -> PriorAuthRequest:
    # Resolve identifiers to UUID primary keys
    pid = _resolve_patient_id(db, patient_id)
    cid = _resolve_coverage_id(db, coverage_id)

    # Requirements snapshot
    requires, required_docs = check_requirements(code)

    # Decide initial status dynamically (no hardcoded codes)
    status, disposition = decide_initial_status(
        db, code=code, requires=requires, coverage_id=cid
    )

    # Persist the request
    par = PriorAuthRequest(
        patient_id=pid,
        coverage_id=cid,
        code=code,
        diagnosis_codes=_csv(diagnosis_codes),
        status=status,
        disposition=disposition,
    )
    db.add(par)
    db.commit()
    db.refresh(par)

    # Attach ephemeral fields for serializer/UI
    par._requires = requires
    par._required_docs = required_docs
    return par
