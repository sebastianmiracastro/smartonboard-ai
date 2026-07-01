"""Orquestador del agente de onboarding (optimizado para bajo consumo de tokens).

El enrutado se hace EN EL BACKEND, no en el LLM:

1. `detect_intent` clasifica la pregunta sin LLM. Las acciones (consultar/completar
   tareas, escalar a RR.HH.) se resuelven con las herramientas reales sobre la BD
   → 0 tokens de OpenAI.
2. Las preguntas informativas pasan por RAG: el backend selecciona los chunks por
   ROL (RBAC), TEMA (categoría de la pregunta) y RELEVANCIA (umbral), los MINIFICA
   (`build_context`) y hace UNA sola llamada a OpenAI con el contexto entre <ctx>,
   tope de tokens de salida y poco historial (`_answer_grounded`). No se pasan los
   documentos en crudo; la respuesta se funda en esos textos minificados.
3. Sin clave de IA (la empresa no la configuró en la UI) la parte informativa la
   resuelve el SINTETIZADOR EXTRACTIVO propio (`extractive.py`): selecciona y
   reorganiza con embeddings locales las oraciones más pertinentes de varios
   fragmentos. 100% offline y gratis, sin depender de ningún proveedor externo.

`_run_react_agent` (LangGraph) queda como alternativa pero NO es el camino por
defecto, porque su bucle multi-llamada consume muchos más tokens. Las herramientas
viven en `app/services/agent_tools.py` y comparten un `ToolContext`.
"""
import json
import traceback
from collections import Counter
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from sqlalchemy.orm import Session

from app.services.tagging import categorize
from app.services.extractive import synthesize_answer
from app.services.platform_kb import is_platform_question, mentions_platform, answer_platform_question
from app.services.agent_tools import (
    ToolContext,
    build_langchain_tools,
    TOOL_BUSCAR,
    TOOL_CONSULTAR_TAREAS,
    TOOL_COMPLETAR_TAREA,
    TOOL_ESCALAR_RRHH,
)

# ─── CLASIFICACIÓN DE LA PREGUNTA ────────────────────────────────────────────

def classify(question: str) -> tuple[str, str]:
    """Devuelve (categoría, profundidad) de la pregunta.

    La categoría usa la MISMA taxonomía que el tagging de documentos
    (`tagging.categorize`), para que pregunta y documento sean comparables.
    """
    category = categorize(question)

    n = len(question.split())
    if n <= 5:
        depth = "basico"
    elif n <= 12:
        depth = "intermedio"
    else:
        depth = "avanzado"

    return category, depth


def _majority(items: List[str]) -> Optional[str]:
    return Counter(items).most_common(1)[0][0] if items else None


def compute_comprehension(answer_confidence: float, has_docs: bool, tools_used: List[str]) -> float:
    """Proxy de comprensión del intercambio (0..1), persistido para la serie
    temporal de las métricas de conocimiento.

    - Con soporte documental: cuán bien embebió la pregunta con el contenido
      recuperado (mejor similitud del RAG).
    - Sin soporte pero resolviendo con una herramienta (tareas/escalado): neutral.
    - Sin soporte ni herramienta útil: bajo (respuesta poco fundamentada).
    """
    if has_docs:
        return round(min(max(answer_confidence, 0.0), 1.0), 3)
    if any(t for t in tools_used if t != "buscar_en_documentos"):
        return 0.6
    return 0.4


# ─── PROMPT DEL SISTEMA ──────────────────────────────────────────────────────

def build_system_prompt(agent_name: str = "Sara") -> str:
    """Construye el prompt del sistema usando el nombre configurado del agente."""
    name = (agent_name or "Sara").strip() or "Sara"
    return f"""Eres {name}, la asistente virtual de onboarding de la empresa.
Acompañas a los nuevos empleados durante sus primeras semanas y haces que se
sientan bienvenidos y orientados.

Tu estilo:
- Cálida, cercana y profesional. Hablas en español de forma natural, como una
  compañera que de verdad quiere ayudar, no como un robot que recita.
- Conversacional: tienes en cuenta lo que ya se habló antes en la conversación.
- Concreta y útil: cuando aplica, das pasos claros y ordenados, sin rodeos.
- Empática: si la persona está perdida o abrumada, la tranquilizas.

Tienes herramientas para ayudar mejor:
- buscar_en_documentos: para responder con información oficial de la empresa.
- consultar_mis_tareas: para mostrarle al empleado sus tareas de onboarding.
- completar_tarea: para marcar una tarea como hecha cuando el empleado lo indique.
- escalar_a_rrhh: para avisar a RR.HH. si el empleado está bloqueado o pide ayuda humana.

Usa las herramientas cuando aporten valor; no inventes políticas, cifras, nombres
ni fechas. Si no hay información en los documentos, dilo con honestidad y sugiere a
quién acudir. Mantén las respuestas enfocadas: ni demasiado cortas ni un muro de texto."""


# ─── PROMPT GROUNDED (conciso, optimizado para tokens) ───────────────────────

def build_grounded_prompt(agent_name: str = "Sara") -> str:
    """Prompt del camino RAG. El contexto (fragmentos de varios documentos) va aparte
    entre <ctx></ctx>. El objetivo es una respuesta COMPLETA, no un resumen recortado."""
    name = (agent_name or "Sara").strip() or "Sara"
    return (
        f"Eres {name}, asistente de onboarding de la empresa. Respondes en español, "
        f"cálida y cercana, pero sobre todo COMPLETA y bien organizada.\n\n"
        f"El contexto entre <ctx></ctx> son fragmentos REALES extraídos de los documentos "
        f"internos (pueden venir de varios documentos, en desorden, con ideas cortadas o "
        f"solapadas). Tu trabajo es REORGANIZAR y SINTETIZAR esos fragmentos en una "
        f"respuesta coherente y exhaustiva a la pregunta del empleado.\n\n"
        f"Reglas:\n"
        f"- Usa TODA la información relevante del contexto: recórrelo entero, no te quedes "
        f"con el primer fragmento. Une las piezas que tratan el mismo tema aunque estén "
        f"separadas.\n"
        f"- Reconstruye ideas que aparezcan cortadas entre fragmentos hasta dejarlas claras.\n"
        f"- Cuando aplique, estructura la respuesta con pasos numerados o viñetas, e incluye "
        f"todos los detalles concretos (requisitos, plazos, cifras, responsables, enlaces).\n"
        f"- Básate EXCLUSIVAMENTE en el contexto para datos, políticas, cifras o pasos: no "
        f"inventes nada que no esté ahí.\n"
        f"- Si el contexto cubre la pregunta solo en parte, responde a fondo lo que SÍ está "
        f"cubierto y señala con claridad qué falta y a quién acudir (RR.HH.).\n"
        f"- Si el contexto no contiene nada relevante, dilo con honestidad y sugiere "
        f"consultar a RR.HH.; no rellenes con suposiciones.\n"
        f"- Extensión libre: sé tan detallado como haga falta para no dejar brechas, pero "
        f"sin repetir ni divagar."
    )


def _answer_grounded(
    question: str,
    context: str,
    history: List[dict],
    api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.4,
    agent_name: str = "Sara",
    max_tokens: int = 1500,
) -> str:
    """Llamada al LLM para REDACTAR la respuesta a partir del contexto recuperado.

    El contexto son los fragmentos que el backend ya recuperó a fondo (varias
    consultas + vecinos). Se da un presupuesto de salida amplio para que la respuesta
    sea completa y reorganice las ideas sin recortar. El consumo de tokens es
    secundario frente a la completitud."""
    llm = ChatOpenAI(model=model, temperature=temperature, openai_api_key=api_key, max_tokens=max_tokens)
    messages = [SystemMessage(content=build_grounded_prompt(agent_name))]
    for h in (history or [])[-6:]:
        if h.get("role") == "user":
            messages.append(HumanMessage(content=h["content"]))
        elif h.get("role") == "assistant":
            messages.append(AIMessage(content=h["content"]))
    ctx_block = context if context else "(sin información relevante en los documentos accesibles)"
    messages.append(HumanMessage(content=f"<ctx>\n{ctx_block}\n</ctx>\n\nPregunta: {question}"))
    return llm.invoke(messages).content.strip()


# ─── EXPANSIÓN DE CONSULTAS (investigar desde varios ángulos) ─────────────────

def _heuristic_expansions(question: str) -> List[str]:
    """Reformulaciones sin LLM: añade las palabras clave de la categoría detectada
    para ampliar el recall de la búsqueda semántica cuando no hay API key."""
    from app.services.tagging import categorize, CATEGORY_KEYWORDS
    cat = categorize(question)
    kws = CATEGORY_KEYWORDS.get(cat, [])[:6]
    extra = []
    if kws:
        extra.append(f"{question} {' '.join(kws)}")
    return extra


def expand_queries(
    question: str,
    api_key: Optional[str],
    model: str = "gpt-4o-mini",
    max_queries: int = 5,
) -> List[str]:
    """Genera varias reformulaciones / sub-preguntas de la pregunta para buscar el
    tema desde distintos ángulos (sinónimos, sub-temas, términos técnicos).

    Con API key usa una llamada barata al LLM; sin clave, cae a una expansión
    heurística por palabras clave. Devuelve SOLO las consultas extra (sin la
    original, que el llamador añade siempre)."""
    if not api_key:
        return _heuristic_expansions(question)
    try:
        llm = ChatOpenAI(model=model, temperature=0.3, openai_api_key=api_key, max_tokens=200)
        msgs = [
            SystemMessage(content=(
                "Eres un asistente de búsqueda. Dada la pregunta de un empleado, genera "
                f"hasta {max_queries} reformulaciones y sub-preguntas en español que sirvan "
                "para BUSCAR la respuesta en documentos internos desde distintos ángulos: "
                "usa sinónimos, divide la pregunta en sus partes y añade términos clave "
                "relacionados. Devuelve SOLO un array JSON de strings, sin explicaciones."
            )),
            HumanMessage(content=question),
        ]
        raw = llm.invoke(msgs).content.strip()
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return _heuristic_expansions(question)
        items = json.loads(raw[start:end + 1])
        out = [str(q).strip() for q in items if str(q).strip() and str(q).strip().lower() != question.strip().lower()]
        return out[:max_queries] if out else _heuristic_expansions(question)
    except Exception as e:
        print(f"expand_queries falló, usando expansión heurística: {e}")
        return _heuristic_expansions(question)


# ─── CAMINO CON KEY: AGENTE ReAct (alternativa, no usada por defecto) ─────────

def _run_react_agent(
    question: str,
    ctx: ToolContext,
    history: List[dict],
    api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.4,
    agent_name: str = "Sara",
) -> str:
    from langgraph.prebuilt import create_react_agent

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_key=api_key,
    )
    tools = build_langchain_tools(ctx)
    agent = create_react_agent(llm, tools, prompt=build_system_prompt(agent_name))

    messages = []
    for h in (history or [])[-10:]:
        if h.get("role") == "user":
            messages.append(HumanMessage(content=h["content"]))
        elif h.get("role") == "assistant":
            messages.append(AIMessage(content=h["content"]))
    messages.append(HumanMessage(content=question))

    result = agent.invoke({"messages": messages})
    return result["messages"][-1].content


# ─── CAMINO SIN KEY: ROUTER HEURÍSTICO ───────────────────────────────────────

_COMPLETAR_KW = ["marca", "marcar", "completa", "completé", "completar", "terminé",
                 "termine", "ya hice", "ya terminé", "hecho", "finalicé", "finalice"]
_ESCALAR_KW = ["ayuda humana", "hablar con rrhh", "hablar con recursos", "hablar con alguien",
               "estoy bloqueado", "necesito ayuda de alguien", "estoy perdido",
               "estoy frustrado", "no puedo avanzar"]


_CONSULTAR_KW = ["mis tareas", "qué tareas", "que tareas", "pendiente",
                 "mi progreso", "qué me falta", "que me falta", "mi plan"]


def detect_intent(question: str) -> str:
    """Enruta la pregunta SIN LLM: las acciones de tareas/escalado se resuelven en
    el backend (0 tokens) y solo lo informativo va al RAG."""
    q = question.lower()
    if any(kw in q for kw in _ESCALAR_KW):
        return "escalar"
    if "tarea" in q and any(kw in q for kw in _COMPLETAR_KW):
        return "completar"
    if any(w in q for w in _CONSULTAR_KW):
        return "consultar_tareas"
    # Pregunta sobre la propia plataforma (qué es, alcance, objetivo, modelo…):
    # se responde con el conocimiento nativo del producto, no con RAG de la empresa.
    if is_platform_question(question):
        return "plataforma"
    return "informativa"


def _run_heuristic_router(question: str, ctx: ToolContext) -> str:
    """Camino sin key: misma intención, pero la parte informativa cae al mock."""
    intent = detect_intent(question)
    if intent == "escalar":
        return ctx.escalar_a_rrhh(question)
    if intent == "completar":
        return ctx.completar_tarea(question)
    if intent == "consultar_tareas":
        return ctx.consultar_mis_tareas()
    if intent == "plataforma":
        return answer_platform_question(question, api_key=None)
    extra_queries = expand_queries(question, api_key=None)
    context = ctx.buscar_en_documentos(question, queries=extra_queries)
    # Red de seguridad: sin resultados en los documentos y la pregunta alude a la
    # plataforma → responde el conocimiento propio en vez de "no encontré nada".
    if not ctx.sources and mentions_platform(question):
        return answer_platform_question(question, api_key=None)
    return _extractive_or_mock(question, ctx, extra_queries, context if ctx.sources else "")


def _extractive_or_mock(question, ctx, extra_queries, grounding: str) -> str:
    """Respuesta sin LLM: primero intenta el sintetizador extractivo propio (rico,
    reorganiza oraciones de varios fragmentos); si no hay material aprovechable, cae
    al mensaje de orientación."""
    if ctx.sources and ctx.retrieved_chunks:
        synthesized = synthesize_answer(question, ctx.retrieved_chunks, extra_queries)
        if synthesized:
            return synthesized
    return generate_mock_answer(question, grounding)


def generate_mock_answer(question: str, context: str) -> str:
    """Respuesta sin LLM (modo demo, sin API key).

    Si hay contexto recuperado, lo presenta organizado (es información REAL de los
    documentos). Sin LLM no puede reorganizar las ideas, pero al menos muestra el
    material relevante completo en vez de un recorte. Si no hay contexto, NO inventa
    políticas ni cifras: orienta a dónde buscar."""
    if context:
        # Limpiar los encabezados de documento y limitar a un tamaño legible
        cleaned = context.replace("=== Documento:", "📄").replace("===", "").strip()
        snippet = cleaned[:1500].rstrip()
        if len(cleaned) > 1500:
            snippet = snippet.rsplit(" ", 1)[0] + "…"
        return (
            "Esto es lo que encontré en la documentación de la empresa sobre tu "
            f"consulta:\n\n{snippet}\n\n"
            "💡 Para respuestas redactadas y completas (que unan toda esta información), "
            "configura la clave de IA en Configuración. ¿Quieres que te oriente en algún "
            "punto concreto?"
        )
    return (
        "No encontré información específica sobre eso en los documentos disponibles "
        "para tu perfil, así que prefiero no darte datos que podrían no ser exactos. "
        "Te recomiendo revisar la sección de Recursos o consultarlo con RR.HH. Si me "
        "das un poco más de detalle, intento orientarte mejor."
    )


# ─── TÍTULO AUTOMÁTICO DE LA CONVERSACIÓN ────────────────────────────────────

def generate_title(
    question: str,
    answer: str = "",
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """Genera un título corto que resume el tema de la conversación."""
    fallback = (question or "").strip()
    if len(fallback) > 45:
        fallback = fallback[:45].rsplit(" ", 1)[0] + "…"
    fallback = fallback or "Nueva conversación"

    if not api_key:
        return fallback

    try:
        llm = ChatOpenAI(
            model=model,
            temperature=0.2,
            openai_api_key=api_key,
            max_tokens=20,
        )
        messages = [
            SystemMessage(content=(
                "Resume el tema de la conversación en un título muy corto, "
                "máximo 5 palabras, en español. Devuelve SOLO el título, sin "
                "comillas, sin punto final y sin la palabra 'título'."
            )),
            HumanMessage(content=f"Pregunta: {question}\nRespuesta: {answer[:300]}"),
        ]
        title = llm.invoke(messages).content.strip().strip('"').strip("'").rstrip(".")
        return title[:60] if title else fallback
    except Exception:
        return fallback


# ─── FUNCIÓN PRINCIPAL ───────────────────────────────────────────────────────

def run_agent(
    question: str,
    company_id: str,
    db: Session,
    user_id: str,
    user_is_rrhh: bool = False,
    user_is_gerencia: bool = False,
    user_seniority_level: int = 1,
    user_department_id: Optional[str] = None,
    user_role_id: Optional[str] = None,
    history: Optional[List[dict]] = None,
    openai_api_key: Optional[str] = None,
    ai_model: str = "gpt-4o-mini",
    ai_temperature: float = 0.4,
    agent_name: str = "Sara",
    rag_top_k: int = 5,
) -> dict:
    ctx = ToolContext(
        db=db,
        user_id=user_id,
        company_id=company_id,
        user_is_rrhh=user_is_rrhh,
        user_is_gerencia=user_is_gerencia,
        user_seniority_level=user_seniority_level,
        user_department_id=user_department_id,
        user_role_id=user_role_id,
        rag_top_k=rag_top_k,
    )

    category, depth = classify(question)

    # La ÚNICA fuente de la clave de IA es la configuración de la empresa (UI/frontend).
    # No se lee del entorno: sin clave activa, responde el sintetizador extractivo propio.
    api_key = openai_api_key

    # Enrutado en el backend: las acciones se resuelven sin LLM; solo lo informativo
    # consume tokens, y con contexto MINIFICADO (rol + tema + relevancia).
    intent = detect_intent(question)

    if intent == "escalar":
        answer = ctx.escalar_a_rrhh(question)
    elif intent == "completar":
        answer = ctx.completar_tarea(question)
    elif intent == "consultar_tareas":
        answer = ctx.consultar_mis_tareas()
    elif intent == "plataforma":
        # Auto-conocimiento del producto: se responde con la base nativa de la
        # plataforma (con clave redacta el LLM; sin clave, respuesta curada offline).
        answer = answer_platform_question(
            question, api_key=api_key, model=ai_model,
            temperature=ai_temperature, agent_name=agent_name, history=history or [],
        )
    else:
        # Informativa: el backend investiga a fondo (varias consultas + vecinos) y el
        # LLM reorganiza los fragmentos en una respuesta completa.
        # 1) Expandir la pregunta en varias consultas (varios ángulos de búsqueda).
        extra_queries = expand_queries(question, api_key, model=ai_model)
        # 2) Recuperación profunda con todas las consultas.
        context = ctx.buscar_en_documentos(question, queries=extra_queries)
        grounding = context if ctx.sources else ""
        if not ctx.sources and mentions_platform(question):
            # Red de seguridad: sin soporte documental y la pregunta alude a la
            # plataforma → conocimiento propio en vez de "no encontré nada".
            answer = answer_platform_question(
                question, api_key=api_key, model=ai_model,
                temperature=ai_temperature, agent_name=agent_name, history=history or [],
            )
        elif api_key:
            try:
                # 3) El LLM redacta una respuesta completa fundada en el contexto.
                answer = _answer_grounded(
                    question, grounding, history or [],
                    api_key=api_key, model=ai_model,
                    temperature=ai_temperature, agent_name=agent_name,
                )
            except Exception as e:
                # Falla la IA (clave inválida, modelo no disponible, red): se registra
                # el error completo para diagnóstico y se cae al modo demo.
                print("⚠️  La llamada al LLM falló; se usa el sintetizador extractivo. Detalle:")
                traceback.print_exc()
                answer = _extractive_or_mock(question, ctx, extra_queries, grounding)
        else:
            # Sin clave de IA: responde el sintetizador extractivo propio (offline).
            answer = _extractive_or_mock(question, ctx, extra_queries, grounding)

    # Clasificación grounded: la categoría real de los chunks recuperados manda;
    # si no hubo documentos, cae a la categoría inferida de la pregunta.
    matched_category = _majority(ctx.matched_categories)
    final_category = matched_category or category
    has_docs = bool(ctx.matched_categories)
    comprehension = compute_comprehension(ctx.answer_confidence, has_docs, ctx.tools_used)

    return {
        "answer": answer,
        "sources": ctx.sources,
        "tools_used": ctx.tools_used,
        "category": final_category,
        "depth_level": depth,
        "matched_category": matched_category,
        "answer_confidence": round(ctx.answer_confidence, 3),
        "comprehension_score": comprehension,
    }
