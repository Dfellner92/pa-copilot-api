from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
import uuid

from app.db import get_db
from app.domain.models import Patient
from app.domain.schemas import PatientCreateIn

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
