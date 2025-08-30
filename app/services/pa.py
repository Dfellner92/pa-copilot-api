from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy import String
from fastapi import HTTPException, status
import uuid

def _try_uuid(v) -> uuid.UUID | None:
    if isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(str(v))
    except Exception:
        return None

def _first_match_row(db, Model, ident: str, candidates: tuple[str, ...]) -> object | None:
    """
    Try a list of candidate string fields first; if none exist or no match,
    scan ANY String column on the model and try equality match.
    Returns an ORM instance or None.
    """
    # Preferred fields first (cheap)
    for field in candidates:
        if hasattr(Model, field):
            try:
                row = db.query(Model).filter(getattr(Model, field) == str(ident)).first()
                if row:
                    return row
            except Exception:
                pass

    # Fallback: inspect all string columns
    try:
        mapper = sa_inspect(Model)
        for prop in mapper.attrs:
            col = getattr(Model, prop.key, None)
            try:
                if hasattr(col, "type") and isinstance(col.type, String):
                    row = db.query(Model).filter(col == str(ident)).first()
                    if row:
                        return row
            except Exception:
                continue
    except Exception:
        pass

    return None

def _resolve_patient_id(db, ident: str | uuid.UUID) -> uuid.UUID:
    uid = _try_uuid(ident)
    try:
        from app.domain.models import Patient  # import inside for safety

        # If it’s already a UUID and exists, we’re done
        if uid:
            row = db.get(Patient, uid)
            if row:
                return row.id

        # Try common patient keys; customize/add if you have a known field
        row = _first_match_row(
            db,
            Patient,
            str(ident),
            candidates=("external_id", "member_id", "patient_id", "mrn", "code", "id_str"),
        )
        if row:
            return row.id

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown patient identifier: {ident!r} (tried UUID and common string keys)",
        )
    except (OperationalError, ProgrammingError, AttributeError) as e:
        # Table/column not ready → return 422 with guidance, not 500
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Patient lookup not configured (missing table/model/column). "
                "Submit a UUID or add a string key column (e.g., member_id/mrn) and seed a row."
            ),
        ) from e

def _resolve_coverage_id(db, ident: str | uuid.UUID) -> uuid.UUID:
    uid = _try_uuid(ident)
    try:
        from app.domain.models import Coverage

        if uid:
            row = db.get(Coverage, uid)
            if row:
                return row.id

        # Try common coverage keys; customize/add to taste
        row = _first_match_row(
            db,
            Coverage,
            str(ident),
            candidates=("external_id", "coverage_id", "plan_id", "policy_number", "code", "id_str"),
        )
        if row:
            return row.id

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown coverage identifier: {ident!r} (tried UUID and common string keys)",
        )
    except (OperationalError, ProgrammingError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Coverage lookup not configured (missing table/model/column). "
                "Submit a UUID or add a string key column (e.g., coverage_id/plan_id) and seed a row."
            ),
        ) from e
