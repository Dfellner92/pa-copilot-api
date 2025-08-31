from uuid import UUID
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db import get_db
from app.domain.schemas import PriorAuthCreateIn  # PriorAuthOut intentionally not used
from app.domain.models import PriorAuthRequest
from app.services.pa import create_pa

router = APIRouter()


def _serialize_par(
    par: PriorAuthRequest,
    *,
    requires_auth: Optional[bool] = None,
    required_docs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Produce a stable shape that the UI can rely on.
    We do NOT use response_model filtering so we can include parity fields.
    """
    # Lazy import to avoid cycles
    from app.services.requirements import check_requirements

    if requires_auth is None or required_docs is None:
        # Recompute (idempotent)
        req, docs = check_requirements(getattr(par, "code", None))
    else:
        req, docs = requires_auth, required_docs or []

    # Optional attributes are guarded with getattr so we don't crash
    member_id = getattr(par, "member_id", None) or getattr(par, "patient_id", None)
    provider_npi = getattr(par, "provider_npi", None)
    provider_name = getattr(par, "provider_name", None)
    member_name = getattr(par, "member_name", None)
    member_dob = getattr(par, "member_dob", None)

    # Attachments (if you model them)
    attachments = []
    try:
        for a in getattr(par, "attachments", []) or []:
            attachments.append(
                {
                    "id": getattr(a, "id", None),
                    "name": getattr(a, "name", None),
                    "url": getattr(a, "url", None),
                }
            )
    except Exception:
        # if relationship not loaded or not present
        attachments = []

    payload: Dict[str, Any] = {
        "id": str(getattr(par, "id")),
        "status": getattr(par, "status", "pending"),
        "disposition": getattr(par, "disposition", None),
        "requiresAuth": bool(req),
        "requiredDocs": docs or [],
        # >>> Parity fields expected by the UI:
        "patient_id": getattr(par, "patient_id", None),
        "coverage_id": getattr(par, "coverage_id", None),
        "code": getattr(par, "code", None),
        "diagnosisCodes": getattr(par, "diagnosis_codes", []) or [],
        # Member / Provider (best-effort)
        "member": {
            "id": str(member_id) if member_id is not None else None,
            "name": member_name,
            "dob": member_dob,
        },
        "provider": {
            "npi": provider_npi,
            "name": provider_name,
        },
        # Convenience mirrors for your mapper’s fallbacks:
        "memberId": str(member_id) if member_id is not None else None,
        "memberName": member_name,
        "providerNpi": provider_npi,
        "providerName": provider_name,
        "codes": [getattr(par, "code")] if getattr(par, "code", None) else [],
        # Timestamps
        "created_at": getattr(par, "created_at", None),
        "updated_at": getattr(par, "updated_at", None) or getattr(par, "created_at", None),
        # Attachments
        "attachments": attachments,
    }

    return payload


@router.post("/requests", status_code=201)
def submit_prior_auth(payload: PriorAuthCreateIn, db: Session = Depends(get_db)):
    """
    Create a request and return a full payload (not filtered by response_model)
    so the UI immediately has patient/coverage/code, etc.
    """
    par = create_pa(
        db,
        patient_id=payload.patient_id,
        coverage_id=payload.coverage_id,
        code=payload.code,
        diagnosis_codes=payload.diagnosis_codes,
    )

    # If create_pa already computed these and stored them transiently, you can pass them in
    requires = getattr(par, "_requires", None)
    required_docs = getattr(par, "_required_docs", None)
    return _serialize_par(par, requires_auth=requires, required_docs=required_docs)


@router.get("/requests/{pa_id}")
def get_prior_auth(pa_id: str, db: Session = Depends(get_db)):
    """
    Return a parity payload for a single request.
    """
    # Normalize and validate the id
    try:
        key = UUID(pa_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Works whether PK is UUID or string
    stmt = select(PriorAuthRequest).where(
        (PriorAuthRequest.id == key) | (PriorAuthRequest.id == str(key))
    )
    par = db.execute(stmt).scalar_one_or_none()
    if not par:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return _serialize_par(par)


@router.get("/requests")
def list_prior_auths(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Keep list behavior but reuse the same serializer to ensure consistency.
    """
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

    items = [_serialize_par(r) for r in rows]
    return {"items": items, "total": total}
