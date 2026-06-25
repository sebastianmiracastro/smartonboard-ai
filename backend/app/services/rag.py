import json
import re
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
    prefer_category: Optional[str] = None,
) -> List[Tuple[str, str, float, Optional[str]]]:
    """Devuelve hasta top_k chunks RELEVANTES como (content, document_id, similitud,
    category). Filtra por RBAC (departamento, rol, seniority, confidencialidad),
    descarta los que no superan el umbral de similitud y, si se indica
    `prefer_category`, prioriza ligeramente los chunks de esa categoría (la del tema
    de la pregunta) sin romper el orden por relevancia real."""
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
            # rank = similitud real + pequeño bono si coincide con el tema preguntado
            boost = 0.05 if (prefer_category and chunk.category == prefer_category) else 0.0
            results.append((chunk.content, chunk.document_id, similarity, chunk.category, similarity + boost))

    # Ordenar por rank (similitud + preferencia) y devolver top_k (sin el rank)
    results.sort(key=lambda x: x[4], reverse=True)
    return [(c, d, sim, cat) for c, d, sim, cat, _rank in results[:top_k]]


def build_context(
    chunks: List[Tuple[str, str, float, Optional[str]]],
    max_total_chars: int = 1400,
    max_chunk_chars: int = 420,
) -> str:
    """Construye un contexto MINIFICADO para el LLM: colapsa espacios, deduplica
    fragmentos casi idénticos (el solape entre chunks) y limita el tamaño total.
    No se pasan los documentos en crudo, solo lo justo para fundamentar la respuesta
    y mantener bajo el consumo de tokens."""
    if not chunks:
        return ""
    seen = set()
    parts: List[str] = []
    total = 0
    for item in chunks:
        text = re.sub(r"\s+", " ", item[0]).strip()
        if not text:
            continue
        if len(text) > max_chunk_chars:
            text = text[:max_chunk_chars].rsplit(" ", 1)[0] + "…"
        key = text[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        if total + len(text) > max_total_chars:
            remaining = max_total_chars - total
            if remaining < 80:
                break
            text = text[:remaining].rsplit(" ", 1)[0] + "…"
        parts.append(text)
        total += len(text)
        if total >= max_total_chars:
            break
    return "\n".join(f"[{i + 1}] {p}" for i, p in enumerate(parts))