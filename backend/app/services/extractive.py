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
# MiniLM asigna una similitud base ~0.30 a casi cualquier frase en español, así que
# el umbral se fija en 0.35 para rechazar ese ruido de fondo (igual que el RAG).
DEFAULT_SENTENCE_THRESHOLD = 0.35

# Fracción de la MEJOR similitud por debajo de la cual una oración se descarta.
# Es un umbral RELATIVO: solo se conservan oraciones cercanas a la más pertinente,
# para que la respuesta tenga foco y no se diluya con frases apenas relacionadas.
RELATIVE_KEEP_RATIO = 0.72

# Igual, pero a nivel de CHUNK (pasaje). El score de un chunk —su mejor oración— es
# una señal más fiable que una oración suelta, así que se descartan enteros los
# pasajes poco relevantes; así se evita pegar frases sueltas de contextos distintos
# (el efecto "Frankenstein" que hacía las respuestas incoherentes).
CHUNK_KEEP_RATIO = 0.85


def clip_to_sentences(text: str, max_chars: int = 1500) -> str:
    """Recorta un texto SIN cortar a media frase: termina en el último final de
    oración que quepa dentro del límite; si no hay ninguno, corta en la última
    palabra completa. Evita los recortes extraños a mitad de palabra."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    ends = list(re.finditer(r"[.!?…](?:\s|$)", window))
    if ends:
        return window[:ends[-1].end()].rstrip()
    return window.rsplit(" ", 1)[0].rstrip() + "…"


def synthesize_answer(
    question: str,
    chunks: List[RetrievedChunk],
    extra_queries: Optional[List[str]] = None,
    max_sentences: int = 16,
    min_similarity: float = DEFAULT_SENTENCE_THRESHOLD,
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

    best = scored[0][0]
    if best < min_similarity:
        # Ninguna oración es realmente pertinente: el llamador dará la respuesta honesta.
        return ""

    # 3) Filtrado por CHUNK: se puntúa cada pasaje por su mejor oración y se conservan
    #    solo los pasajes cercanos al mejor. Así no se cuelan frases sueltas de
    #    contextos poco relevantes (evita el efecto "Frankenstein").
    sim_by_i = {i: sim for sim, i in scored}
    chunk_best = {}
    for sim, i in scored:
        key = (origin[i][0], origin[i][1])  # (document_id, chunk_index)
        if sim > chunk_best.get(key, -1.0):
            chunk_best[key] = sim
    overall_best = max(chunk_best.values())
    chunk_cutoff = max(min_similarity, overall_best * CHUNK_KEEP_RATIO)
    kept_chunks = {k for k, s in chunk_best.items() if s >= chunk_cutoff}

    # 4) Dentro de esos pasajes, conserva las oraciones pertinentes (umbral relativo
    #    a la mejor) en su ORDEN original, para que cada pasaje se lea de corrido.
    sent_cutoff = max(min_similarity, overall_best * RELATIVE_KEEP_RATIO)
    relevant = [
        i for i in range(len(sentences))
        if (origin[i][0], origin[i][1]) in kept_chunks and sim_by_i[i] >= sent_cutoff
    ]
    if not relevant:
        return ""
    relevant = relevant[:max_sentences]

    # Reordena: pasaje más relevante primero, luego el orden natural del texto.
    ordered = sorted(
        relevant,
        key=lambda i: (-chunk_best[(origin[i][0], origin[i][1])],
                       origin[i][0], origin[i][1], origin[i][2]),
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
