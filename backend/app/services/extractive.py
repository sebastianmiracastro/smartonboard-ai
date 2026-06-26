"""Sintetizador extractivo propio de SmartOnboard (sin LLM, 100% local y gratis).

Es la "IA de la casa" que responde cuando la empresa NO ha configurado una clave de
IA. En vez de devolver un recorte crudo, construye una respuesta RICA y coherente:

  1. Parte los fragmentos recuperados (de varios documentos) en oraciones.
  2. Embebe cada oración con el MISMO modelo del RAG (all-MiniLM-L6-v2) — gratis y
     offline — y la puntúa contra la pregunta y todas sus reformulaciones,
     quedándose con la mejor similitud (la oración que responde a cualquier ángulo
     cuenta).
  3. Selecciona las oraciones más pertinentes (umbral + tope generoso), deduplica el
     solape entre fragmentos y las REORDENA por documento y posición original para
     que el texto se lea de corrido, no como piezas sueltas.
  4. Ensambla la respuesta agrupando oraciones contiguas en párrafos.

Es extractivo (no inventa: toda frase proviene de los documentos), lo que lo hace
fiable y defendible. Cuando sí hay clave de IA, este mismo material recuperado se le
pasa al LLM para una redacción abstractiva; el extractivo es el piso de calidad que
garantiza que SIEMPRE haya una respuesta fundamentada.
"""
import re
from typing import List, Optional

from app.services.embeddings import generate_embedding, generate_embeddings_batch, cosine_similarity
from app.services.rag import RetrievedChunk


# Corta en oraciones respetando los finales típicos (., !, ?, :, ;) y los saltos de
# línea / viñetas (listas). No parte abreviaturas comunes a propósito por simplicidad.
_SENT_SPLIT = re.compile(r"(?<=[\.\!\?\:\;])\s+|\n+")
_BULLET = re.compile(r"^\s*([\-•\*]|\d+[\.\)])\s+")


def _split_sentences(text: str) -> List[str]:
    out: List[str] = []
    for raw in _SENT_SPLIT.split(text or ""):
        s = re.sub(r"\s+", " ", raw).strip()
        # quita viñeta/numeral inicial para que el embedding evalúe el contenido
        s = _BULLET.sub("", s).strip()
        if len(s) >= 25:  # descarta encabezados/ruido muy cortos
            out.append(s)
    return out


def _norm(sentence: str) -> str:
    """Texto normalizado (minúsculas, sin puntuación, espacios colapsados) para
    comparar oraciones por contención y descartar el solape entre fragmentos."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9áéíóúñ ]", " ", sentence.lower())).strip()


# Por debajo de esta similitud una oración no se considera pertinente a la pregunta.
DEFAULT_SENTENCE_THRESHOLD = 0.30


def synthesize_answer(
    question: str,
    chunks: List[RetrievedChunk],
    extra_queries: Optional[List[str]] = None,
    max_sentences: int = 16,
    min_similarity: float = DEFAULT_SENTENCE_THRESHOLD,
    min_keep: int = 5,
) -> str:
    """Construye una respuesta extractiva rica a partir de los fragmentos recuperados.

    Devuelve "" si no hay material aprovechable (el llamador decide el fallback)."""
    if not chunks:
        return ""

    # 1) Oraciones con su procedencia (para reordenar y agrupar después)
    candidates: List[tuple] = []  # (sent, norm, origin)
    for ch in chunks:
        for pos, sent in enumerate(_split_sentences(ch.content)):
            norm = _norm(sent)
            if norm:
                candidates.append((sent, norm, (ch.document_id, ch.chunk_index, pos)))

    # Deduplicación por CONTENCIÓN: el solape entre fragmentos produce trozos que son
    # subcadena de una oración más larga. Procesando de mayor a menor longitud, se
    # descarta todo lo que ya esté contenido en una oración conservada.
    candidates.sort(key=lambda c: len(c[1]), reverse=True)
    sentences: List[str] = []
    origin: List[tuple] = []
    kept_norms: List[str] = []
    for sent, norm, org in candidates:
        if any(norm in k for k in kept_norms):
            continue
        kept_norms.append(norm)
        sentences.append(sent)
        origin.append(org)

    if not sentences:
        return ""

    # 2) Puntuar cada oración contra la pregunta y sus reformulaciones (mejor sim)
    queries = [question] + [q for q in (extra_queries or []) if q and q.strip()]
    query_embeddings = [generate_embedding(q) for q in queries]
    sent_embeddings = generate_embeddings_batch(sentences)

    scored = []
    for i, emb in enumerate(sent_embeddings):
        sim = max(cosine_similarity(qe, emb) for qe in query_embeddings)
        scored.append((sim, i))
    scored.sort(reverse=True)

    # 3) Selección: las que superan el umbral, con tope generoso; si pasan muy pocas,
    #    conserva al menos `min_keep` (respuesta completa sin dejar brechas).
    relevant = [i for sim, i in scored if sim >= min_similarity][:max_sentences]
    if len(relevant) < min_keep:
        relevant = [i for _sim, i in scored[:min_keep]]
    selected = set(relevant)

    # 4) Reordenar por procedencia (documento más relevante primero, luego orden
    #    natural del texto) para que la lectura sea coherente.
    doc_best = {}
    for sim, i in scored:
        d = origin[i][0]
        doc_best[d] = max(doc_best.get(d, 0.0), sim)
    ordered = sorted(
        relevant,
        key=lambda i: (-doc_best[origin[i][0]], origin[i][0], origin[i][1], origin[i][2]),
    )

    # 5) Agrupar oraciones contiguas (mismo doc, índices cercanos) en párrafos
    paragraphs: List[str] = []
    current: List[str] = []
    prev = None
    for i in ordered:
        d, ci, _ = origin[i]
        if prev is not None and (d != prev[0] or abs(ci - prev[1]) > 1):
            paragraphs.append(" ".join(current))
            current = []
        current.append(sentences[i])
        prev = (d, ci)
    if current:
        paragraphs.append(" ".join(current))

    body = "\n\n".join(paragraphs)
    return (
        "Esto es lo que dice la documentación de la empresa sobre tu consulta:\n\n"
        f"{body}\n\n"
        "¿Quieres que profundice en algún punto en concreto?"
    )
