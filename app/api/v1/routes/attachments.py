from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db import get_db
from app.domain.schemas import DocumentRefOut
from app.domain.models import DocumentReference
from app.services.files import store_document
from app.adapters import storage_local

router = APIRouter()

@router.post("", response_model=DocumentRefOut, status_code=201)
async def upload_attachment(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Save the file and DB record
    doc = store_document(db, filename=file.filename, content_type=file.content_type or "", file_stream=file.file)
    # Local dev URL for download
    url = f"/v1/attachments/{doc.id}"
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "url": url,
    }

@router.get("/{doc_id}")
def download_attachment(doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(DocumentReference, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if not storage_local.exists(doc.storage_key):
        raise HTTPException(status_code=410, detail="File missing")
    f = storage_local.open_file(doc.storage_key)
    return Response(content=f.read(), media_type=doc.content_type, headers={
        "Content-Disposition": f'attachment; filename="{doc.filename}"'
    })
