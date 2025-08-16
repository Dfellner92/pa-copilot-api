import uuid
from app.db import get_db
from app.domain.models import Patient, Coverage

def _seed_patient_and_coverage():
    db = next(get_db())
    p = Patient(id=uuid.uuid4(), first_name="Jane", last_name="Doe", birth_date="1990-01-01")
    c = Coverage(id=uuid.uuid4(), member_id="M123", plan="Gold PPO", payer="ACME", patient_id=p.id)
    db.add(p); db.add(c); db.commit()
    return str(p.id), str(c.id)


def test_create_prior_auth(client, db_session):
    p = Patient(id=uuid.uuid4(), first_name="Jane", last_name="Doe", birth_date="1990-01-01")
    c = Coverage(id=uuid.uuid4(), member_id="M123", plan="Gold PPO", payer="ACME", patient_id=p.id)
    db_session.add_all([p, c])
    db_session.commit()

    payload = {
        "patient_id": str(p.id),
        "coverage_id": str(c.id),
        "code": "70553",
        "diagnosis_codes": ["G43.909"]
    }
    r = client.post("/v1/prior-auth/requests", json=payload)
    assert r.status_code == 201, r.text
