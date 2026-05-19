from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import Document, User
from app.schemas.schemas import DocumentOut
from app.core.dependencies import get_current_user, require_rrhh

router = APIRouter(prefix="/api/documents", tags=["Documentos"])

@router.get("/", response_model=List[DocumentOut])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document).filter(
        Document.company_id == current_user.company_id
    )
    if current_user.system_role not in ["rrhh", "gerencia"]:
        query = query.filter(
            Document.require_rrhh == False,
            Document.require_gerencia == False
        )
    return query.all()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    content = await file.read()
    size_kb = len(content) // 1024
    ext = file.filename.split(".")[-1].lower() if file.filename else "txt"

    doc = Document(
        company_id=current_user.company_id,
        name=file.filename,
        format=ext,
        size_kb=size_kb,
        status="en_cola",
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"mensaje": "Documento subido", "id": doc.id, "nombre": doc.name}

@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    db.delete(doc)
    db.commit()
    return {"mensaje": "Documento eliminado"}