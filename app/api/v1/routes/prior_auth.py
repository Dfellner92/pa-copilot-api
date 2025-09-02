from uuid import UUID
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import get_db
from app.domain.schemas import PriorAuthCreateIn  # keep input schema only
from app.domain.models import PriorAuthRequest
from app.services.pa import create_pa

router = APIRouter()


# --- Optional related models (best-effort imports) ---
try:
    # Adjust these names to whatever your models are actually called
    from app.domain.models import Patient as _Patient  # or Member
except Exception:
    _Patient = None  # type: ignore

try:
    from app.domain.models import Provider as _Provider
except Exception:
    _Provider = None  # type: ignore


def _enrich_member_provider(db: Session, par: PriorAuthRequest) -> Dict[str, Optional[str]]:
    """Lookup member/provider names if not already on the row."""
    member_id = getattr(par, "member_id", None) or getattr(par, "patient_id", None)
    member_name = getattr(par, "member_name", None)
    member_dob = getattr(par, "member_dob", None)
    provider_npi = getattr(par, "provider_npi", None)
    provider_name = getattr(par, "provider_name", None)

    # Member enrichment
    if (member_name is None or member_dob is None) and _Patient is not None and member_id:
        try:
            row = db.execute(select(_Patient).where(
                (_Patient.id == member_id) | (_Patient.id == str(member_id))
            )).scalar_one_or_none()
            if row is not None:
                # Try common attribute names
                member_name = member_name or getattr(row, "full_name", None) or getattr(row, "name", None)
                member_dob  = member_dob  or getattr(row, "dob", None) or getattr(row, "date_of_birth", None)
        except Exception:
            pass  # don't fail the request if enrichment fails

    # Provider enrichment
    if provider_name is None and _Provider is not None and provider_npi:
        try:
            prow = db.execute(select(_Provider).where(
                (_Provider.npi == provider_npi) | (_Provider.id == provider_npi)
            )).scalar_one_or_none()
            if prow is not None:
                provider_name = getattr(prow, "name", None)
        except Exception:
            pass

    return {
        "member_id": str(member_id) if member_id is not None else None,
        "member_name": member_name,
        "member_dob": member_dob,
        "provider_npi": provider_npi,
        "provider_name": provider_name,
    }


def _serialize_par(
    db: Session,
    par: PriorAuthRequest,
    *,
    requires_auth: Optional[bool] = None,
    required_docs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Stable, enriched shape that the UI expects."""
    from app.services.requirements import check_requirements

    if requires_auth is None or required_docs is None:
        req, docs = check_requirements(getattr(par, "code", None))
    else:
        req, docs = requires_auth, required_docs or []

    # Enrich from related tables when missing
    enrich = _enrich_member_provider(db, par)

    attachments = []
    try:
        for a in getattr(par, "attachments", []) or []:
            attachments.append(
                {"id": getattr(a, "id", None), "name": getattr(a, "name", None), "url": getattr(a, "url", None)}
            )
    except Exception:
        pass

    payload: Dict[str, Any] = {
        "id": str(getattr(par, "id")),
        "status": getattr(par, "status", "pending"),
        "disposition": getattr(par, "disposition", None),
        "requiresAuth": bool(req),
        "requiredDocs": docs or [],
        # parity/ids
        "patient_id": getattr(par, "patient_id", None),
        "coverage_id": getattr(par, "coverage_id", None),
        "code": getattr(par, "code", None),
        "diagnosisCodes": getattr(par, "diagnosis_codes", []) or [],
        # member / provider (prefer denormalized columns on PAR, then enrichment)
        "member": {
            "id": str(getattr(par, "member_id", None) or getattr(par, "patient_id", None) or enrich["member_id"])
            if (getattr(par, "member_id", None) or getattr(par, "patient_id", None) or enrich["member_id"])
            else None,
            "name": getattr(par, "member_name", None) or enrich["member_name"],
            "dob": getattr(par, "member_dob", None) or enrich["member_dob"],
        },
        "provider": {
            "npi": getattr(par, "provider_npi", None) or enrich["provider_npi"],
            "name": getattr(par, "provider_name", None) or enrich["provider_name"],
        },
        # mirrors for your mapper fallbacks
        "memberId": enrich["member_id"] or getattr(par, "member_id", None) or getattr(par, "patient_id", None),
        "memberName": getattr(par, "member_name", None) or enrich["member_name"],
        "providerNpi": getattr(par, "provider_npi", None) or enrich["provider_npi"],
        "providerName": getattr(par, "provider_name", None) or enrich["provider_name"],
        "codes": [getattr(par, "code")] if getattr(par, "code", None) else [],
        # timestamps
        "created_at": getattr(par, "created_at", None),
        "updated_at": getattr(par, "updated_at", None) or getattr(par, "created_at", None),
        # attachments
        "attachments": attachments,
    }
    return payload


@router.post("/requests", status_code=201)
def submit_prior_auth(payload: PriorAuthCreateIn, db: Session = Depends(get_db)):
    par = create_pa(
        db,
        patient_id=payload.patient_id,
        coverage_id=payload.coverage_id,
        code=payload.code,
        diagnosis_codes=payload.diagnosis_codes,
    )
    requires = getattr(par, "_requires", None)
    required_docs = getattr(par, "_required_docs", None)
    return _serialize_par(db, par, requires_auth=requires, required_docs=required_docs)


@router.get("/requests/{pa_id}")
def get_prior_auth(pa_id: str, db: Session = Depends(get_db)):
    # Accept UUIDs in string or UUID column
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
    rows = (
        q.order_by(PriorAuthRequest.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = [_serialize_par(db, r) for r in rows]
    return {"items": items, "total": total}
