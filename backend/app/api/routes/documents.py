from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.services.tagging import CATEGORIES
from app.db.database import get_db, SessionLocal
from app.models.models import Document, User, Company, Role, Department
from app.schemas.schemas import DocumentOut
from app.core.dependencies import get_current_user, require_rrhh
from app.services.document_processor import extract_text, chunk_text
from app.services.embeddings import generate_embeddings_batch
from app.services.rag import index_document_chunks
from app.services.tagging import tag_document

router = APIRouter(prefix="/api/documents", tags=["Documentos"])

def process_document_background(
    document_id: str,
    company_id: str,
    file_bytes: bytes,
    file_format: str,
    manual_category: Optional[str] = None,
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

        chunks = chunk_text(text)  # contextos coherentes (parámetros por defecto)
        if not chunks:
            doc.status = "error"
            db.commit()
            return

        doc.progress = 50
        db.commit()

        embeddings = generate_embeddings_batch(chunks)

        doc.progress = 70
        db.commit()

        # Categorización temática: etiqueta cada chunk (categoría/tema/complejidad)
        # y mapea el documento a los cargos relevantes (LLM si hay clave, si no [] = todos).
        company = db.query(Company).filter(Company.id == company_id).first()
        roles = [
            {"id": r.id, "name": r.name}
            for r in db.query(Role).join(Department, Role.department_id == Department.id)
            .filter(Department.company_id == company_id).all()
        ]
        tagging = tag_document(
            doc_name=doc.name,
            chunks=chunks,
            roles=roles,
            api_key=company.openai_api_key if company else None,
            model=(company.ai_model if company else None) or "gpt-4o-mini",
        )

        # Categoría: si RR.HH. la fijó manualmente, manda sobre la auto-detectada
        if manual_category in CATEGORIES:
            for t in tagging["chunks"]:
                t["category"] = manual_category
            doc.primary_category = manual_category
        else:
            doc.primary_category = tagging["primary_category"]

        # Si el documento se restringió a un cargo (acceso), ese cargo también define
        # su relevancia temática para las métricas.
        if doc.role_permission:
            target_roles = [doc.role_permission]
            cargo_json = json.dumps(target_roles)
            for t in tagging["chunks"]:
                t["cargo_ids"] = cargo_json
        else:
            target_roles = tagging["target_role_ids"]
        doc.target_role_ids = json.dumps(target_roles)

        doc.progress = 85
        db.commit()

        count = index_document_chunks(
            db, document_id, company_id, chunks, embeddings, tags=tagging["chunks"]
        )

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
    if current_user.system_role == "gerencia":
        pass  # gerencia ve todo
    elif current_user.system_role == "rrhh":
        query = query.filter(Document.require_gerencia == False)
    else:
        seniority = current_user.role.seniority_level if current_user.role else 1
        query = query.filter(
            Document.require_rrhh == False,
            Document.require_gerencia == False,
        ).filter(
            (Document.min_seniority == None) | (Document.min_seniority <= seniority)
        ).filter(
            (Document.dept_permission == None) | (Document.dept_permission == current_user.department_id)
        ).filter(
            (Document.role_permission == None) | (Document.role_permission == current_user.role_id)
        )
    return query.all()

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),          # categoría de conocimiento (una de las 5) o auto
    role_permission: Optional[str] = Form(None),   # cargo específico, o vacío = general
    dept_permission: Optional[str] = Form(None),   # departamento específico, o vacío = general
    min_seniority: Optional[int] = Form(None),
    require_rrhh: bool = Form(False),
    require_gerencia: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    file_bytes = await file.read()
    size_kb = len(file_bytes) // 1024
    ext = file.filename.split(".")[-1].lower() if file.filename else "txt"

    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Formato no soportado. Use PDF, DOCX o TXT.")

    # Normalizar vacíos a None
    category = category or None
    role_permission = role_permission or None
    dept_permission = dept_permission or None

    if category and category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Categoría inválida.")
    if role_permission:
        role = db.query(Role).join(Department, Role.department_id == Department.id).filter(
            Role.id == role_permission, Department.company_id == current_user.company_id
        ).first()
        if not role:
            raise HTTPException(status_code=400, detail="Cargo inválido para tu empresa.")
    if dept_permission:
        dept = db.query(Department).filter(
            Department.id == dept_permission, Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Departamento inválido para tu empresa.")

    doc = Document(
        company_id=current_user.company_id,
        name=file.filename,
        format=ext,
        size_kb=size_kb,
        status="en_cola",
        uploaded_by=current_user.id,
        require_rrhh=require_rrhh,
        require_gerencia=require_gerencia,
        role_permission=role_permission,
        dept_permission=dept_permission,
        min_seniority=min_seniority,
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
        category,
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