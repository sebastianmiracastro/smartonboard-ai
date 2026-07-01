"""Sintetizador extractivo propio de SmartOnboard (sin LLM, 100% local y gratis).

Es la "IA de la casa" que responde cuando la empresa NO ha configurado una clave de
IA. En vez de devolver un recorte crudo, construye una respuesta RICA y coherente:

  1. Parte los fragmentos por LÍNEAS (los ítems de lista/pasos quedan intactos) y
     solo la prosa se sub-divide en oraciones.
  2. Embebe cada oración con el MISMO modelo del RAG (all-MiniLM-L6-v2) — gratis y
     offline — y la puntúa contra la pregunta y todas sus reformulaciones (mejor sim).
  3. Filtra por pasaje relevante (chunk-gating) y arma un pool de oraciones
     pertinentes; en un pasaje relevante conserva la enumeración COMPLETA de pasos.
  4. Selecciona con MMR (relevancia + diversidad): las más pertinentes pero SIN
     repetir la misma idea cuando varios documentos la mencionan.
  5. Reordena por pasaje/posición y ensambla, PRESERVANDO las listas como viñetas.

Es extractivo (no inventa: toda frase proviene de los documentos), lo que lo hace
fiable y defendible. Cuando sí hay clave de IA, este mismo material recuperado se le
pasa al LLM para una redacción abstractiva; el extractivo es el piso de calidad que
garantiza que SIEMPRE haya una respuesta fundamentada.
"""
import random
import re
from typing import List, Optional

from app.services.embeddings import generate_embedding, generate_embeddings_batch, cosine_similarity
from app.services.rag import RetrievedChunk


# Corta en oraciones respetando los finales típicos (., !, ?, :, ;) y los saltos de
# línea / viñetas (listas). No parte abreviaturas comunes a propósito por simplicidad.
_SENT_SPLIT = re.compile(r"(?<=[\.\!\?\:\;])\s+|\n+")
_BULLET = re.compile(r"^\s*([\-•\*]|\d+[\.\)])\s+")
# Sub-división de una LÍNEA de prosa en oraciones (solo tras . ! ?, no listas).
_WITHIN_LINE = re.compile(r"(?<=[\.\!\?])\s+")


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
# Es un umbral RELATIVO. Se busca una respuesta RICA: se conservan las oraciones
# razonablemente pertinentes (no solo las cercanísimas a la mejor). El umbral base
# (min_similarity) + el MMR (sin redundancia) evitan el ruido y la repetición.
RELATIVE_KEEP_RATIO = 0.62

# Igual, pero a nivel de CHUNK (pasaje). Se prioriza la RIQUEZA: se incluyen todos
# los pasajes razonablemente pertinentes que el RAG ya recuperó (proceso + cantidad
# + acumulación de un mismo tema). El filtro fino DENTRO del pasaje (RELATIVE) evita
# meter frases sueltas ajenas; el umbral base descarta lo claramente irrelevante.
CHUNK_KEEP_RATIO = 0.6


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


# Peso relevancia↔diversidad del MMR (0.72 = prioriza responder, pero sin repetir).
MMR_LAMBDA = 0.72
# Por encima de esta similitud entre dos oraciones, se consideran la MISMA idea.
DUPLICATE_THRESHOLD = 0.9


def _mmr_select(pool: List[int], sim_by_i: dict, embeddings: list,
                k: int, lambda_: float = MMR_LAMBDA) -> List[int]:
    """Selección por Relevancia Marginal Máxima (MMR): elige las oraciones más
    pertinentes PERO diversas entre sí, descartando las casi idénticas. Evita que la
    respuesta repita la misma idea cuando varios documentos la mencionan."""
    pool = sorted(pool, key=lambda i: sim_by_i[i], reverse=True)
    selected = [pool.pop(0)]
    while pool and len(selected) < k:
        best_i, best_score = None, None
        for i in pool:
            redundancy = max(cosine_similarity(embeddings[i], embeddings[j]) for j in selected)
            if redundancy >= DUPLICATE_THRESHOLD:
                continue  # casi idéntica a una ya elegida → no aporta
            score = lambda_ * sim_by_i[i] - (1 - lambda_) * redundancy
            if best_score is None or score > best_score:
                best_i, best_score = i, score
        if best_i is None:
            break  # lo que queda es todo redundante
        selected.append(best_i)
        pool.remove(best_i)
    return selected


def _render_group(group: List[int], sentences: List[str], is_list: List[bool]) -> str:
    """Ensambla un grupo de oraciones contiguas. Si NINGUNA venía como lista, se une
    en un párrafo. Si hay pasos/viñetas, se respeta la estructura: la prosa como
    líneas y los ítems de lista con viñeta (no un párrafo corrido)."""
    if not any(is_list[i] for i in group):
        return " ".join(sentences[i] for i in group)
    return "\n".join(f"• {sentences[i]}" if is_list[i] else sentences[i] for i in group)


def synthesize_answer(
    question: str,
    chunks: List[RetrievedChunk],
    extra_queries: Optional[List[str]] = None,
    max_sentences: int = 24,
    min_similarity: float = DEFAULT_SENTENCE_THRESHOLD,
) -> str:
    """Construye una respuesta extractiva rica a partir de los fragmentos recuperados.

    Devuelve "" si no hay material aprovechable (el llamador decide el fallback)."""
    if not chunks:
        return ""

    # 1) Oraciones con su procedencia y si venían como ítem de lista/paso.
    #    Se divide por LÍNEAS (los ítems de lista quedan intactos) y solo la PROSA se
    #    sub-divide en oraciones. Así un "1. Escribe…" no se parte en "1." + "Escribe…".
    candidates: List[tuple] = []  # (sent, norm, origin, is_list)
    for ch in chunks:
        pos = 0
        for line in (ch.content or "").split("\n"):
            line = line.strip()
            if not line:
                continue
            was_list = bool(_BULLET.match(line))
            if was_list:
                units = [_BULLET.sub("", line).strip()]
            else:
                units = [re.sub(r"\s+", " ", u).strip() for u in _WITHIN_LINE.split(line)]
            for s in units:
                # Los pasos suelen ser cortos: se permite menos longitud si era lista.
                if len(s) < (12 if was_list else 22):
                    continue
                norm = _norm(s)
                if norm:
                    candidates.append((s, norm, (ch.document_id, ch.chunk_index, pos), was_list))
                    pos += 1

    # Deduplicación por CONTENCIÓN (solape entre fragmentos): descarta lo que ya está
    # contenido en una oración más larga conservada.
    candidates.sort(key=lambda c: len(c[1]), reverse=True)
    sentences: List[str] = []
    origin: List[tuple] = []
    is_list: List[bool] = []
    kept_norms: List[str] = []
    for sent, norm, org, was_list in candidates:
        if any(norm in k for k in kept_norms):
            continue
        kept_norms.append(norm)
        sentences.append(sent)
        origin.append(org)
        is_list.append(was_list)

    if not sentences:
        return ""

    # 2) Puntuar cada oración contra la pregunta y sus reformulaciones (mejor sim).
    queries = [question] + [q for q in (extra_queries or []) if q and q.strip()]
    query_embeddings = [generate_embedding(q) for q in queries]
    sent_embeddings = generate_embeddings_batch(sentences)

    scored = sorted(
        ((max(cosine_similarity(qe, emb) for qe in query_embeddings), i)
         for i, emb in enumerate(sent_embeddings)),
        reverse=True,
    )
    best = scored[0][0]
    if best < min_similarity:
        # Ninguna oración es realmente pertinente: el llamador dará la respuesta honesta.
        return ""
    sim_by_i = {i: sim for sim, i in scored}

    # 3) Filtrado por CHUNK: se conservan solo los pasajes cercanos al mejor (evita
    #    frases sueltas de contextos poco relevantes → el efecto "Frankenstein").
    chunk_best: dict = {}
    for sim, i in scored:
        key = (origin[i][0], origin[i][1])
        chunk_best[key] = max(chunk_best.get(key, -1.0), sim)
    overall_best = max(chunk_best.values())
    chunk_cutoff = max(min_similarity, overall_best * CHUNK_KEEP_RATIO)
    kept_chunks = {k for k, s in chunk_best.items() if s >= chunk_cutoff}

    # 4) Pool de oraciones pertinentes (umbral relativo a la mejor) dentro de esos pasajes.
    sent_cutoff = max(min_similarity, overall_best * RELATIVE_KEEP_RATIO)
    pool = [
        i for i in range(len(sentences))
        if (origin[i][0], origin[i][1]) in kept_chunks
        # En un pasaje relevante se conservan TODOS los ítems de lista/pasos (una
        # enumeración se responde completa); la prosa sí pasa el umbral relativo.
        and (is_list[i] or sim_by_i[i] >= sent_cutoff)
    ]
    if not pool:
        return ""

    # 4b) MMR: quedarse con las más pertinentes PERO diversas (sin repetir la idea).
    selected = _mmr_select(pool, sim_by_i, sent_embeddings, k=max_sentences)

    # 5) Reordenar (pasaje más relevante primero, luego orden natural) y ensamblar,
    #    preservando las listas/pasos como viñetas.
    ordered = sorted(
        selected,
        key=lambda i: (-chunk_best[(origin[i][0], origin[i][1])],
                       origin[i][0], origin[i][1], origin[i][2]),
    )
    paragraphs: List[str] = []
    group: List[int] = []
    prev = None
    for i in ordered:
        d, ci, _ = origin[i]
        if prev is not None and (d != prev[0] or abs(ci - prev[1]) > 1):
            paragraphs.append(_render_group(group, sentences, is_list))
            group = []
        group.append(i)
        prev = (d, ci)
    if group:
        paragraphs.append(_render_group(group, sentences, is_list))

    body = "\n\n".join(paragraphs)
    return f"{random.choice(_INTROS)}\n\n{body}\n\n{random.choice(_CLOSINGS)}"


# Intros/cierres variados para que la respuesta extractiva no suene repetitiva.
_INTROS = [
    "Esto es lo que dice la documentación de la empresa sobre tu consulta:",
    "Encontré esto en los documentos de la empresa:",
    "Según la documentación disponible para tu perfil:",
]
_CLOSINGS = [
    "¿Quieres que profundice en algún punto en concreto?",
    "Si necesitas más detalle sobre algo puntual, dímelo.",
    "¿Te sirve, o busco algo más específico?",
]
