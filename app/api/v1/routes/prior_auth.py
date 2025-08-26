from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.domain.schemas import PriorAuthCreateIn, PriorAuthOut
from app.domain.models import PriorAuthRequest
from app.services.pa import create_pa

router = APIRouter()

@router.post("/requests", response_model=PriorAuthOut, status_code=201)
def submit_prior_auth(payload: PriorAuthCreateIn, db: Session = Depends(get_db)):
    # (Optionally: validate patient/coverage exist)
    par = create_pa(
        db,
        patient_id=payload.patient_id,
        coverage_id=payload.coverage_id,
        code=payload.code,
        diagnosis_codes=payload.diagnosis_codes,
    )
    return {
        "id": str(par.id),
        "status": par.status,
        "disposition": par.disposition,
        "requiresAuth": getattr(par, "_requires", True),
        "requiredDocs": getattr(par, "_required_docs", []),
    }

@router.get("/requests/{pa_id}", response_model=PriorAuthOut)
def get_prior_auth(pa_id: str, db: Session = Depends(get_db)):
    par = db.query(PriorAuthRequest).get(pa_id)
    if not par:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    # recompute requires/docs for convenience (idempotent)
    from app.services.requirements import check_requirements
    requires, required_docs = check_requirements(par.code)
    return {
        "id": str(par.id),
        "status": par.status,
        "disposition": par.disposition,
        "requiresAuth": requires,
        "requiredDocs": required_docs,
    }

@router.get("/requests")
def list_prior_auths(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(PriorAuthRequest)
    if status:
        q = q.filter(PriorAuthRequest.status == status)
    rows = q.order_by(PriorAuthRequest.id.desc()).offset(offset).limit(limit).all()

    out = []
    from app.services.requirements import check_requirements
    for r in rows:
        requires, docs = check_requirements(r.code)
        out.append({
            "id": str(r.id),
            "status": r.status,                    # e.g. "pending"
            "disposition": getattr(r, "disposition", None),
            "requiresAuth": requires,
            "requiredDocs": docs,
            "memberName": getattr(r, "member_name", None),
            "memberId": getattr(r, "member_id", None),
            "providerName": getattr(r, "provider_name", None),
            "codes": [r.code],
            "updatedAt": getattr(r, "updated_at", None) or getattr(r, "created_at", None),
        })
    return {"items": out, "total": q.count()}
