from sqlalchemy.orm import Session
from app.adapters import storage_local
from app.domain.models import DocumentReference

def store_document(db: Session, *, filename: str, content_type: str, file_stream) -> DocumentReference:
    storage_key, size = storage_local.save_file(file_stream, content_type, filename)
    doc = DocumentReference(
        filename=filename,
        content_type=content_type or "application/octet-stream",
        size_bytes=size,
        storage_key=storage_key,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc