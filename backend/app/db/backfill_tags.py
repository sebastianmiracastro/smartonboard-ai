"""Backfill de la categorización temática.

Re-etiqueta los documentos/chunks ya indexados (antes de existir el tagging) y
rellena la categoría de los mensajes de chat históricos, para que las métricas de
conocimiento tengan datos desde el primer momento.

Uso:
    venv\\Scripts\\activate
    python -m app.db.backfill_tags
"""
import json
from app.db.database import SessionLocal
from app.models.models import (
    Document, DocumentChunk, Company, Role, Department,
    Conversation, ChatMessage,
)
from app.services.tagging import tag_chunk, tag_document, categorize


def backfill_documents(db) -> int:
    """Re-etiqueta chunks y documentos indexados que aún no tienen categoría."""
    docs = db.query(Document).filter(Document.status == "indexado").all()
    updated = 0
    for doc in docs:
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id
        ).order_by(DocumentChunk.chunk_index).all()
        if not chunks:
            continue

        company = db.query(Company).filter(Company.id == doc.company_id).first()
        roles = [
            {"id": r.id, "name": r.name}
            for r in db.query(Role).join(Department, Role.department_id == Department.id)
            .filter(Department.company_id == doc.company_id).all()
        ]
        result = tag_document(
            doc_name=doc.name,
            chunks=[c.content for c in chunks],
            roles=roles,
            api_key=company.openai_api_key if company else None,
            model=(company.ai_model if company else None) or "gpt-4o-mini",
        )
        for chunk, tag in zip(chunks, result["chunks"]):
            chunk.category = tag["category"]
            chunk.topic = tag["topic"]
            chunk.complexity = tag["complexity"]
            chunk.cargo_ids = tag["cargo_ids"]
        doc.primary_category = result["primary_category"]
        doc.target_role_ids = json.dumps(result["target_role_ids"])
        updated += 1
        db.commit()
    return updated


def backfill_messages(db) -> int:
    """Rellena category/comprehension de mensajes históricos (aproximado).

    La categoría se infiere del texto de la pregunta; la comprensión se aproxima
    según si la respuesta citó fuentes. Solo toca lo que está vacío.
    """
    updated = 0
    convs = db.query(Conversation).all()
    for conv in convs:
        msgs = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conv.id
        ).order_by(ChatMessage.created_at).all()

        last_question = None
        for m in msgs:
            if m.role == "user":
                last_question = m.content
                if not m.category:
                    m.category = categorize(m.content)
                    updated += 1
            elif m.role == "assistant":
                if not m.category and last_question:
                    m.category = categorize(last_question)
                    updated += 1
                if m.comprehension_score is None:
                    has_sources = bool(m.sources and m.sources not in ("[]", "null"))
                    m.comprehension_score = 0.5 if has_sources else 0.4
                    updated += 1
        db.commit()
    return updated


def main():
    db = SessionLocal()
    try:
        d = backfill_documents(db)
        print(f"Documentos re-etiquetados: {d}")
        m = backfill_messages(db)
        print(f"Campos de mensajes rellenados: {m}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
