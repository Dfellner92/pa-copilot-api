from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid

from app.db import get_db
from app.domain.models import Patient, Coverage
from app.domain.schemas import CoverageCreateIn

router = APIRouter()

def _coverage_to_out(c: Coverage):
    return {
        "id": str(c.id),
        "external_id": c.external_id,
        "member_id": c.member_id,
        "plan": c.plan,
        "payer": c.payer,
        "patient_id": str(c.patient_id),
    }

@router.post("/coverages", status_code=201)
def create_coverage(
    payload: CoverageCreateIn,
    db: Session = Depends(get_db),
):
    # Check if patient exists
    try:
        patient_uuid = uuid.UUID(payload.patient_id)
        patient = db.get(Patient, patient_uuid)
    except Exception:
        patient = db.query(Patient).filter(Patient.external_id == payload.patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Check if external_id already exists
    existing = db.query(Coverage).filter(Coverage.external_id == payload.external_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="external_id already exists")

    c = Coverage(
        external_id=payload.external_id,
        member_id=payload.member_id,
        plan=payload.plan,
        payer=payload.payer,
        patient_id=patient.id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _coverage_to_out(c)

@router.get("/coverages/{ident}")
def get_coverage(ident: str, db: Session = Depends(get_db)):
    # accept UUID or external_id
    try:
        key = uuid.UUID(str(ident))
        row = db.get(Coverage, key)
    except Exception:
        row = db.query(Coverage).filter(Coverage.external_id == ident).first()

    if not row:
        raise HTTPException(status_code=404, detail="Coverage not found")

    return _coverage_to_out(row)
