from fastapi import APIRouter, Depends
from app.db import ping_db, get_db
from app.domain.models import Patient
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("")
def db_check():
    ping_db()
    return {"database": "ok"}


@router.post("/seed-patient")
def seed_patient(db: Session = Depends(get_db)):
    p = Patient(first_name="Jane", last_name="Doe", birth_date="1981-04-12")
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": str(p.id)}

@router.get("/patients")
def list_patients(db: Session = Depends(get_db)):
    rows = db.query(Patient).all()
    return [{"id": str(r.id), "first_name": r.first_name, "last_name": r.last_name} for r in rows]