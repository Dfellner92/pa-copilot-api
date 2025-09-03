from uuid import UUID
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import get_db
from app.domain.schemas import PriorAuthCreateIn
from app.domain.models import PriorAuthRequest, Patient
from app.services.pa import create_pa

router = APIRouter()


def _to_list_from_csv(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [p.strip() for p in str(val).split(",") if p.strip()]


def _serialize_par(
    db: Session,
    par: PriorAuthRequest,
    *,
    requires_auth: Optional[bool] = None,
    required_docs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Stable, enriched shape for the UI."""
    from app.services.requirements import check_requirements

    if requires_auth is None or required_docs is None:
        req, docs = check_requirements(getattr(par, "code", None))
    else:
        req, docs = requires_auth, (required_docs or [])

    # Use loaded relationship if present; otherwise look it up once
    patient = getattr(par, "patient", None)
    if patient is None and getattr(par, "patient_id", None):
        try:
            patient = (
                db.execute(
                    select(Patient).where(
                        (Patient.id == par.patient_id) | (Patient.id == str(par.patient_id))
                    )
                )
                .scalar_one_or_none()
            )
        except Exception:
            patient = None

    member_id = str(getattr(par, "patient_id", "")) or None
    member_name = None
    member_dob = None
    if patient is not None:
        first = getattr(patient, "first_name", None)
        last = getattr(patient, "last_name", None)
        if first or last:
            member_name = " ".join([p for p in [first, last] if p])
        member_dob = getattr(patient, "birth_date", None)

    diagnosis_list = _to_list_from_csv(getattr(par, "diagnosis_codes", None))

    return {
        "id": str(getattr(par, "id")),
        "status": getattr(par, "status", "pending"),
        "disposition": getattr(par, "disposition", None),
        "requiresAuth": bool(req),
        "requiredDocs": docs,
        # core ids / codes
        "patient_id": getattr(par, "patient_id", None),
        "coverage_id": getattr(par, "coverage_id", None),
        "code": getattr(par, "code", None),
        "diagnosisCodes": diagnosis_list,
        # member (and mirrors used by the UI mapper)
        "member": {"id": member_id, "name": member_name, "dob": member_dob},
        "memberId": member_id,
        "memberName": member_name,
        # provider isn’t modeled yet; keep keys present
        "provider": {"npi": None, "name": None},
        "providerNpi": None,
        "providerName": None,
        # conveniences
        "codes": [getattr(par, "code")] if getattr(par, "code", None) else [],
        "attachments": [],
    }


@router.post("/requests", status_code=201)
def submit_prior_auth(payload: PriorAuthCreateIn, db: Session = Depends(get_db)):
    par = create_pa(
        db,
        patient_id=payload.patient_id,
        coverage_id=payload.coverage_id,
        code=payload.code,
        diagnosis_codes=payload.diagnosis_codes,
        provider_name=payload.provider_name,
        provider_npi=payload.provider_npi,
    )
    requires = getattr(par, "_requires", None)
    required_docs = getattr(par, "_required_docs", None)
    return _serialize_par(db, par, requires_auth=requires, required_docs=required_docs)


@router.get("/requests/{pa_id}")
def get_prior_auth(pa_id: str, db: Session = Depends(get_db)):
    try:
        key = UUID(pa_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    stmt = select(PriorAuthRequest).where(
        (PriorAuthRequest.id == key) | (PriorAuthRequest.id == str(key))
    )
    par = db.execute(stmt).scalar_one_or_none()
    if not par:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return _serialize_par(db, par)


@router.get("/requests")
def list_prior_auths(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PriorAuthRequest)
    if status:
        q = q.filter(PriorAuthRequest.status == status)
    total = q.count()
    rows = q.order_by(PriorAuthRequest.id.desc()).offset(offset).limit(limit).all()
    items = [_serialize_par(db, r) for r in rows]
    return {"items": items, "total": total}
