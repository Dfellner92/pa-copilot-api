from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid

from app.db import get_db
from app.domain.models import Patient, Coverage
from app.domain.schemas import PatientCreateIn, CoverageCreateIn

router = APIRouter()

def _row_to_out(p: Patient):
    return {
        "id": str(p.id),
        "external_id": p.external_id,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "birth_date": p.birth_date,
        # convenience mirrors the UI likes
        "name": f"{p.first_name} {p.last_name}".strip(),
        "dob": p.birth_date,
    }

def _coverage_to_out(c: Coverage):
    return {
        "id": str(c.id),
        "external_id": c.external_id,
        "member_id": c.member_id,
        "plan": c.plan,
        "payer": c.payer,
        "patient_id": str(c.patient_id),
    }

@router.post("/patients", status_code=201)
def create_patient(
    payload: PatientCreateIn,
    db: Session = Depends(get_db),
):
    # enforce uniqueness on external_id (schema already has unique index)
    existing = db.query(Patient).filter(Patient.external_id == payload.external_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="external_id already exists")

    p = Patient(
        external_id=payload.external_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        birth_date=payload.birth_date,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _row_to_out(p)

# NEW: Coverage creation endpoint
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

@router.get("/patients/{ident}")
def get_patient(ident: str, db: Session = Depends(get_db)):
    # accept UUID or external_id
    try:
        key = uuid.UUID(str(ident))
        row = db.get(Patient, key)
    except Exception:
        row = db.query(Patient).filter(Patient.external_id == ident).first()

    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")

    return _row_to_out(row)
