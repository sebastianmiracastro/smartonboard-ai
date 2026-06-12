from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db, SessionLocal
from app.models.models import Document, User
from app.schemas.schemas import DocumentOut
from app.core.dependencies import get_current_user, require_rrhh
from app.services.document_processor import extract_text, chunk_text
from app.services.embeddings import generate_embeddings_batch
from app.services.rag import index_document_chunks

router = APIRouter(prefix="/api/documents", tags=["Documentos"])

def process_document_background(
    document_id: str,
    company_id: str,
    file_bytes: bytes,
    file_format: str,
):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return
        doc.status = "procesando"
        doc.progress = 10
        db.commit()

        text = extract_text(file_bytes, file_format)
        if not text.strip():
            doc.status = "error"
            db.commit()
            return

        doc.progress = 30
        db.commit()

        chunks = chunk_text(text, chunk_size=500, overlap=50)
        if not chunks:
            doc.status = "error"
            db.commit()
            return

        doc.progress = 50
        db.commit()

        embeddings = generate_embeddings_batch(chunks)

        doc.progress = 80
        db.commit()

        count = index_document_chunks(db, document_id, company_id, chunks, embeddings)

        doc.status = "indexado"
        doc.progress = 100
        doc.chunk_count = count
        db.commit()

    except Exception as e:
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "error"
                db.commit()
        except Exception:
            pass
        print(f"Error procesando documento: {e}")
    finally:
        db.close()

@router.get("/", response_model=List[DocumentOut])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Document).filter(
        Document.company_id == current_user.company_id
    )
    if current_user.system_role not in ["rrhh", "gerencia"]:
        seniority = current_user.role.seniority_level if current_user.role else 1
        query = query.filter(
            Document.require_rrhh == False,
            Document.require_gerencia == False,
        ).filter(
            (Document.min_seniority == None) | (Document.min_seniority <= seniority)
        ).filter(
            (Document.dept_permission == None) | (Document.dept_permission == current_user.department_id)
        )
    return query.all()

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    require_rrhh: bool = False,
    require_gerencia: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    file_bytes = await file.read()
    size_kb = len(file_bytes) // 1024
    ext = file.filename.split(".")[-1].lower() if file.filename else "txt"

    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Formato no soportado. Use PDF, DOCX o TXT.")

    doc = Document(
        company_id=current_user.company_id,
        name=file.filename,
        format=ext,
        size_kb=size_kb,
        status="en_cola",
        uploaded_by=current_user.id,
        require_rrhh=require_rrhh,
        require_gerencia=require_gerencia,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Procesar en segundo plano
    background_tasks.add_task(
        process_document_background,
        doc.id,
        current_user.company_id,
        file_bytes,
        ext,
    )

    return {
        "mensaje": "Documento subido y en proceso de indexación",
        "id": doc.id,
        "nombre": doc.name
    }

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