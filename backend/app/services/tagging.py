"""Categorización temática de contenido y preguntas.

Centraliza la taxonomía (5 categorías fijas) que usan TANTO el tagging de los
documentos en la ingesta COMO la clasificación de las preguntas del usuario, de
modo que pregunta y documento "hablen el mismo idioma". Esto es la base para las
métricas de comprensión, cobertura y pérdida de conocimiento.

Estrategia: heurístico determinista siempre disponible (sin API key) y, cuando hay
clave de empresa, un refinamiento opcional a nivel de documento con el LLM para
mapear el contenido a los cargos reales de la empresa.
"""
import json
import unicodedata
from collections import Counter
from typing import List, Optional

# ─── TAXONOMÍA FIJA ──────────────────────────────────────────────────────────

CATEGORIES = ["procesos", "rol", "cultura", "herramientas", "relaciones"]
DEFAULT_CATEGORY = "procesos"

# Información legible de cada categoría (para la UI de parametrización). La taxonomía
# es FIJA por diseño: garantiza comparabilidad de las métricas entre cargos y en el tiempo.
CATEGORY_INFO = [
    {"key": "procesos", "label": "Procesos", "description": "Procedimientos, trámites y flujos de trabajo de la empresa."},
    {"key": "rol", "label": "Rol", "description": "Responsabilidades, funciones y objetivos del cargo."},
    {"key": "cultura", "label": "Cultura", "description": "Políticas, normas, beneficios y valores de la organización."},
    {"key": "herramientas", "label": "Herramientas", "description": "Sistemas, software y accesos que usa el empleado."},
    {"key": "relaciones", "label": "Relaciones", "description": "Equipo, líderes, contactos y estructura de reporte."},
]

# Palabras clave por categoría (sin acentos; el texto se normaliza antes)
CATEGORY_KEYWORDS = {
    "procesos": [
        "proceso", "procedimiento", "paso", "pasos", "flujo", "como funciona",
        "solicitud", "solicitar", "aprobacion", "formulario", "tramite", "gestion",
        "registrar", "diligenciar", "ciclo",
    ],
    "rol": [
        "responsabilidad", "funcion", "rol", "cargo", "debo hacer", "objetivo",
        "meta", "kpi", "entregable", "puesto", "desempeno", "competencia",
    ],
    "cultura": [
        "politica", "norma", "beneficio", "vacacion", "permiso", "valor", "valores",
        "cultura", "horario", "codigo de conducta", "bienestar", "salario", "nomina",
        "contrato", "licencia", "incapacidad",
    ],
    "herramientas": [
        "jira", "slack", "git", "github", "gitlab", "herramienta", "sistema",
        "configurar", "software", "plataforma", "vpn", "correo", "aplicacion",
        "acceso", "credencial", "instalar", "api",
    ],
    "relaciones": [
        "quien", "equipo", "reporto", "reportar", "lider", "jefe", "companero",
        "contacto", "area", "organigrama", "supervisor", "mentor", "buddy",
    ],
}

_STOPWORDS = {
    "para", "con", "los", "las", "del", "una", "uno", "que", "como", "por", "este",
    "esta", "esto", "son", "sus", "sera", "debe", "puede", "tiene", "hay", "muy",
    "mas", "menos", "entre", "sobre", "cada", "todo", "toda", "todos", "todas",
    "cuando", "donde", "porque", "tambien", "segun", "desde", "hasta", "pero",
    "fragmento", "informacion", "documento", "empresa", "tu", "tus", "nuestro",
}

_AVANZADO_HINTS = [
    "arquitectura", "configuracion avanzada", "despliegue", "kubernetes", "pipeline",
    "integracion", "algoritmo", "optimizacion", "seguridad", "infraestructura",
    "escalabilidad", "microservicio", "protocolo", "cifrado", "autenticacion",
]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


# ─── CATEGORÍA ───────────────────────────────────────────────────────────────

def categorize(text: str) -> str:
    """Devuelve la categoría con más coincidencias de palabras clave."""
    norm = _normalize(text)
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in norm:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else DEFAULT_CATEGORY


def category_scores(text: str) -> dict:
    """Conteo de coincidencias por categoría (útil para depurar/ponderar)."""
    norm = _normalize(text)
    return {
        cat: sum(1 for kw in kws if kw in norm)
        for cat, kws in CATEGORY_KEYWORDS.items()
    }


# ─── COMPLEJIDAD ─────────────────────────────────────────────────────────────

def detect_complexity(text: str) -> str:
    norm = _normalize(text)
    n = len(norm.split())
    if any(h in norm for h in _AVANZADO_HINTS) or n > 90:
        return "avanzado"
    if n < 35:
        return "basico"
    return "intermedio"


# ─── TEMA (grano fino) ───────────────────────────────────────────────────────

def extract_topic(text: str, max_words: int = 4) -> str:
    """Tema corto = palabras significativas más frecuentes del fragmento."""
    norm = _normalize(text)
    words = [
        w for w in norm.replace(",", " ").replace(".", " ").split()
        if len(w) >= 4 and w not in _STOPWORDS and w.isalpha()
    ]
    if not words:
        return ""
    most = [w for w, _ in Counter(words).most_common(max_words)]
    return " ".join(most)


# ─── TAGGING DE UN CHUNK (heurístico, siempre disponible) ────────────────────

def tag_chunk(content: str) -> dict:
    return {
        "category": categorize(content),
        "topic": extract_topic(content),
        "complexity": detect_complexity(content),
    }


# ─── CARGOS RELEVANTES A NIVEL DE DOCUMENTO ──────────────────────────────────

def infer_target_roles_llm(
    doc_name: str,
    sample_text: str,
    roles: List[dict],
    api_key: str,
    model: str = "gpt-4o-mini",
) -> Optional[List[str]]:
    """Con API key: pide al LLM qué cargos de la empresa son relevantes para el
    documento. Devuelve lista de role_id, [] si aplica a todos, o None si falla."""
    if not api_key or not roles:
        return None
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        catalog = "\n".join(f"- {r['id']}: {r['name']}" for r in roles)
        llm = ChatOpenAI(model=model, temperature=0, openai_api_key=api_key, max_tokens=120)
        msgs = [
            SystemMessage(content=(
                "Eres un clasificador de documentos de onboarding. Dado el nombre y un "
                "extracto de un documento, y el catálogo de cargos de la empresa, indica "
                "a qué cargos aplica el contenido. Devuelve SOLO un array JSON de ids de "
                "cargo (p. ej. [\"id1\",\"id2\"]). Si aplica a TODOS los cargos, devuelve []."
            )),
            HumanMessage(content=(
                f"Documento: {doc_name}\n\nExtracto:\n{sample_text[:1200]}\n\n"
                f"Cargos disponibles:\n{catalog}"
            )),
        ]
        raw = llm.invoke(msgs).content.strip()
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return None
        ids = json.loads(raw[start:end + 1])
        valid = {r["id"] for r in roles}
        return [i for i in ids if i in valid]
    except Exception as e:
        print(f"infer_target_roles_llm falló, se omiten cargos: {e}")
        return None


def tag_document(
    doc_name: str,
    chunks: List[str],
    roles: Optional[List[dict]] = None,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> dict:
    """Etiqueta todos los chunks de un documento y resume el doc.

    Devuelve {
      "chunks": [{category, topic, complexity}, ...],
      "primary_category": str,
      "target_role_ids": [str, ...],   # [] = todos los cargos
    }
    """
    chunk_tags = [tag_chunk(c) for c in chunks]

    # Categoría dominante del documento = mayoría entre sus chunks
    if chunk_tags:
        primary = Counter(t["category"] for t in chunk_tags).most_common(1)[0][0]
    else:
        primary = DEFAULT_CATEGORY

    # Cargos: refinar con LLM si hay clave; si no, [] (aplica a todos)
    target_roles: List[str] = []
    if api_key and roles:
        sample = "\n".join(chunks[:3])
        inferred = infer_target_roles_llm(doc_name, sample, roles, api_key, model)
        if inferred is not None:
            target_roles = inferred

    # Cada chunk hereda los cargos del documento
    cargo_json = json.dumps(target_roles)
    for t in chunk_tags:
        t["cargo_ids"] = cargo_json

    return {
        "chunks": chunk_tags,
        "primary_category": primary,
        "target_role_ids": target_roles,
    }
