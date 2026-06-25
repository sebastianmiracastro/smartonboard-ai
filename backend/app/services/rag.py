import json
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.models import DocumentChunk, Document
from app.services.embeddings import generate_embedding, cosine_similarity

def index_document_chunks(
    db: Session,
    document_id: str,
    company_id: str,
    chunks: List[str],
    embeddings: List[List[float]],
    tags: Optional[List[dict]] = None,
) -> int:
    """Indexa los chunks con su embedding y sus etiquetas temáticas.

    `tags[i]` (opcional) = {category, topic, complexity, cargo_ids} para chunk i.
    """
    # Eliminar chunks anteriores del documento
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).delete()

    # Insertar nuevos chunks
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        tag = tags[i] if tags and i < len(tags) else {}
        doc_chunk = DocumentChunk(
            document_id=document_id,
            company_id=company_id,
            content=chunk,
            chunk_index=i,
            embedding=json.dumps(embedding),
            category=tag.get("category"),
            topic=tag.get("topic"),
            complexity=tag.get("complexity"),
            cargo_ids=tag.get("cargo_ids"),
        )
        db.add(doc_chunk)

    db.commit()
    return len(chunks)

# Por debajo de esta similitud un chunk se considera NO relevante para la pregunta.
# Evita que el agente "lea documentos" enteros: solo recibe contextos pertinentes.
# Calibrado para all-MiniLM-L6-v2: coincidencias reales ~0.45-0.75, ruido ~0.15-0.29.
DEFAULT_MIN_SIMILARITY = 0.35


def search_similar_chunks(
    db: Session,
    company_id: str,
    query: str,
    user_is_rrhh: bool = False,
    user_is_gerencia: bool = False,
    user_seniority_level: int = 1,
    user_department_id: str = None,
    user_role_id: str = None,
    top_k: int = 5,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> List[Tuple[str, str, float, Optional[str]]]:
    """Devuelve hasta top_k chunks RELEVANTES como (content, document_id, similitud,
    category). Filtra por RBAC (departamento, rol, seniority, confidencialidad) y
    descarta los que no superan el umbral de similitud."""
    # Generar embedding de la pregunta
    query_embedding = generate_embedding(query)

    # Obtener documentos accesibles para el usuario
    doc_query = db.query(Document).filter(
        Document.company_id == company_id,
        Document.status == "indexado"
    )

    if not user_is_rrhh and not user_is_gerencia:
        doc_query = doc_query.filter(
            Document.require_rrhh == False,
            Document.require_gerencia == False,
        ).filter(
            (Document.min_seniority == None) | (Document.min_seniority <= user_seniority_level)
        ).filter(
            (Document.dept_permission == None) | (Document.dept_permission == user_department_id)
        ).filter(
            (Document.role_permission == None) | (Document.role_permission == user_role_id)
        )
    elif user_is_rrhh and not user_is_gerencia:
        doc_query = doc_query.filter(
            Document.require_gerencia == False
        )

    accessible_docs = [d.id for d in doc_query.all()]

    if not accessible_docs:
        return []

    # Obtener chunks de documentos accesibles
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.company_id == company_id,
        DocumentChunk.document_id.in_(accessible_docs)
    ).all()

    if not chunks:
        return []

    # Calcular similitud con cada chunk
    results = []
    for chunk in chunks:
        if not chunk.embedding:
            continue
        chunk_embedding = json.loads(chunk.embedding)
        similarity = cosine_similarity(query_embedding, chunk_embedding)
        # Solo contextos relevantes (por encima del umbral)
        if similarity >= min_similarity:
            results.append((chunk.content, chunk.document_id, similarity, chunk.category))

    # Ordenar por similitud y retornar top_k
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_k]

def build_context(chunks: List[Tuple[str, str, float, Optional[str]]]) -> str:
    if not chunks:
        return ""
    context = "Información relevante de los documentos de la empresa:\n\n"
    for i, item in enumerate(chunks):
        content = item[0]
        context += f"[Fragmento {i+1}]:\n{content}\n\n"
    return context