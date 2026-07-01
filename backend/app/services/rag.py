import json
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
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
# Calibrado para all-MiniLM-L6-v2: coincidencias reales ~0.45-0.75, ruido ~0.15-0.29.
DEFAULT_MIN_SIMILARITY = 0.35
# En el camino PROFUNDO (multi-consulta) bajamos un poco el piso: cada fragmento se
# valida contra varias reformulaciones de la pregunta, así que una coincidencia algo
# más débil con alguna de ellas sigue siendo señal útil sin meter ruido.
DEEP_MIN_SIMILARITY = 0.26


@dataclass
class RetrievedChunk:
    """Un fragmento recuperado, con la metadata que necesitan el contexto y las
    métricas de conocimiento."""
    content: str
    document_id: str
    similarity: float
    category: Optional[str]
    chunk_index: int
    is_neighbor: bool = False  # traído por continuidad, no por relevancia directa


# ─── RBAC: documentos accesibles para el usuario ─────────────────────────────

def accessible_document_ids(
    db: Session,
    company_id: str,
    user_is_rrhh: bool = False,
    user_is_gerencia: bool = False,
    user_seniority_level: int = 1,
    user_department_id: str = None,
    user_role_id: str = None,
) -> List[str]:
    """Ids de documentos INDEXADOS que el usuario puede ver según el RBAC
    (departamento, rol, seniority y flags de confidencialidad)."""
    doc_query = db.query(Document).filter(
        Document.company_id == company_id,
        Document.status == "indexado",
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
        doc_query = doc_query.filter(Document.require_gerencia == False)

    return [d.id for d in doc_query.all()]


def _load_accessible_chunks(
    db: Session, company_id: str, doc_ids: List[str]
) -> List[DocumentChunk]:
    if not doc_ids:
        return []
    return db.query(DocumentChunk).filter(
        DocumentChunk.company_id == company_id,
        DocumentChunk.document_id.in_(doc_ids),
    ).all()


# ─── RECUPERACIÓN PROFUNDA (multi-consulta + vecinos) ────────────────────────

def deep_retrieve(
    db: Session,
    company_id: str,
    queries: List[str],
    user_is_rrhh: bool = False,
    user_is_gerencia: bool = False,
    user_seniority_level: int = 1,
    user_department_id: str = None,
    user_role_id: str = None,
    max_chunks: int = 20,
    min_similarity: float = DEEP_MIN_SIMILARITY,
    neighbor_radius: int = 1,
    prefer_category: Optional[str] = None,
) -> List[RetrievedChunk]:
    """Recuperación a fondo: NO se queda con la primera coincidencia.

    1. Lanza VARIAS consultas (reformulaciones/sub-preguntas de la original) y
       puntúa todos los chunks accesibles contra cada una, quedándose con la mejor
       similitud por chunk (un fragmento que responde a cualquier ángulo cuenta).
    2. Toma los `max_chunks` mejores por relevancia.
    3. Añade los fragmentos VECINOS (mismo documento, índice ±`neighbor_radius`) de
       cada uno, aunque no superen el umbral, para no cortar ideas a la mitad: el
       LLM recibe el contexto continuo, no recortes sueltos.
    4. Devuelve la lista lista para ensamblar (ordenada por relevancia; el orden de
       lectura coherente lo impone `build_rich_context` por documento e índice).
    """
    queries = [q.strip() for q in queries if q and q.strip()]
    if not queries:
        return []

    doc_ids = accessible_document_ids(
        db, company_id, user_is_rrhh, user_is_gerencia,
        user_seniority_level, user_department_id, user_role_id,
    )
    chunks = _load_accessible_chunks(db, company_id, doc_ids)
    if not chunks:
        return []

    # Embeddings de los chunks parseados una sola vez
    parsed: List[Tuple[DocumentChunk, List[float]]] = []
    by_position: Dict[Tuple[str, int], DocumentChunk] = {}
    for ch in chunks:
        if not ch.embedding:
            continue
        try:
            emb = json.loads(ch.embedding)
        except (ValueError, TypeError):
            continue
        parsed.append((ch, emb))
        by_position[(ch.document_id, ch.chunk_index)] = ch

    if not parsed:
        return []

    # Embeddings de cada consulta (la original + sus reformulaciones)
    query_embeddings = [generate_embedding(q) for q in queries]

    # Mejor similitud de cada chunk contra CUALQUIERA de las consultas
    best_sim: Dict[int, float] = {}
    best_meta: Dict[int, DocumentChunk] = {}
    for ch, emb in parsed:
        sim = max(cosine_similarity(qe, emb) for qe in query_embeddings)
        if sim >= min_similarity:
            cid = id(ch)
            best_sim[cid] = sim
            best_meta[cid] = ch

    if not best_sim:
        return []

    # Orden por relevancia (con un pequeño bono al tema de la pregunta) y corte
    def _rank(cid: int) -> float:
        ch = best_meta[cid]
        boost = 0.05 if (prefer_category and ch.category == prefer_category) else 0.0
        return best_sim[cid] + boost

    top_ids = sorted(best_sim.keys(), key=_rank, reverse=True)[:max_chunks]

    selected: Dict[Tuple[str, int], RetrievedChunk] = {}
    for cid in top_ids:
        ch = best_meta[cid]
        selected[(ch.document_id, ch.chunk_index)] = RetrievedChunk(
            content=ch.content,
            document_id=ch.document_id,
            similarity=best_sim[cid],
            category=ch.category,
            chunk_index=ch.chunk_index,
            is_neighbor=False,
        )

    # Vecinos: continuidad de lectura sin cortar ideas
    if neighbor_radius > 0:
        for (doc_id, idx) in list(selected.keys()):
            for off in range(-neighbor_radius, neighbor_radius + 1):
                if off == 0:
                    continue
                pos = (doc_id, idx + off)
                if pos in selected:
                    continue
                neighbor = by_position.get(pos)
                if neighbor is None:
                    continue
                selected[pos] = RetrievedChunk(
                    content=neighbor.content,
                    document_id=neighbor.document_id,
                    similarity=0.0,
                    category=neighbor.category,
                    chunk_index=neighbor.chunk_index,
                    is_neighbor=True,
                )

    return sorted(
        selected.values(),
        key=lambda r: (r.similarity, not r.is_neighbor),
        reverse=True,
    )


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
) -> List[RetrievedChunk]:
    """Búsqueda simple de una sola consulta (compatibilidad). Para el chat se usa
    `deep_retrieve`, que investiga a fondo con varias reformulaciones."""
    return deep_retrieve(
        db=db,
        company_id=company_id,
        queries=[query],
        user_is_rrhh=user_is_rrhh,
        user_is_gerencia=user_is_gerencia,
        user_seniority_level=user_seniority_level,
        user_department_id=user_department_id,
        user_role_id=user_role_id,
        max_chunks=top_k,
        min_similarity=min_similarity,
        neighbor_radius=0,
        prefer_category=prefer_category,
    )


# ─── ENSAMBLADO DEL CONTEXTO PARA EL LLM ─────────────────────────────────────

def _normalize_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r", " ")).strip()


def build_rich_context(
    chunks: List[RetrievedChunk],
    doc_names: Optional[Dict[str, str]] = None,
    max_total_chars: int = 40000,
) -> str:
    """Ensambla un contexto COMPLETO y legible para que el LLM reorganice las ideas.

    A diferencia del enfoque minimalista anterior (que recortaba a ~1400 chars y
    truncaba cada fragmento), aquí se prioriza la COMPLETITUD:
    - Agrupa los fragmentos por documento y los ordena por su índice → el texto se
      lee de corrido, como en el documento original, no como recortes sueltos.
    - Deduplica el solape entre fragmentos contiguos.
    - Mantiene un presupuesto amplio (consume más tokens a propósito) para no dejar
      brechas de información.
    """
    if not chunks:
        return ""
    doc_names = doc_names or {}

    # Agrupar por documento, ordenar por índice (lectura coherente)
    by_doc: Dict[str, List[RetrievedChunk]] = {}
    doc_best_sim: Dict[str, float] = {}
    for ch in chunks:
        by_doc.setdefault(ch.document_id, []).append(ch)
        doc_best_sim[ch.document_id] = max(doc_best_sim.get(ch.document_id, 0.0), ch.similarity)
    for doc_id in by_doc:
        by_doc[doc_id].sort(key=lambda r: r.chunk_index)

    # Documentos más relevantes primero
    ordered_docs = sorted(by_doc.keys(), key=lambda d: doc_best_sim[d], reverse=True)

    parts: List[str] = []
    total = 0
    for doc_id in ordered_docs:
        name = doc_names.get(doc_id, "Documento")
        header = f"\n=== Documento: {name} ==="
        segments: List[str] = []
        prev_tail = ""
        for ch in by_doc[doc_id]:
            text = _normalize_ws(ch.content)
            if not text:
                continue
            # Deduplicar el solape con el fragmento anterior del mismo documento
            if prev_tail and text.startswith(prev_tail[:40]):
                text = text[len(prev_tail):].lstrip()
                if not text:
                    continue
            segments.append(text)
            prev_tail = text[-80:]
        if not segments:
            continue
        block = header + "\n" + " ".join(segments)
        if total + len(block) > max_total_chars:
            remaining = max_total_chars - total
            if remaining < 200:
                break
            block = block[:remaining].rsplit(" ", 1)[0] + "…"
            parts.append(block)
            break
        parts.append(block)
        total += len(block)

    return "\n".join(parts).strip()


# Compatibilidad: el nombre anterior sigue disponible para llamadas simples.
def build_context(chunks: List[RetrievedChunk], **kwargs) -> str:
    return build_rich_context(chunks, **kwargs)
