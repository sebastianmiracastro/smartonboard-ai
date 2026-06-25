"""Orquestador del agente de onboarding.

Dos caminos según haya o no OPENAI_API_KEY:

- CON key  → agente ReAct real (`create_react_agent` de LangGraph) que decide de
  forma autónoma qué herramienta usar vía function-calling de gpt-4o-mini.
- SIN key  → router heurístico de intención que invoca las MISMAS herramientas
  reales (sobre la BD) y, si la pregunta es informativa, cae al pipeline RAG+mock
  original. Así las herramientas son demostrables sin depender del LLM.

En ambos casos las herramientas viven en `app/services/agent_tools.py` y comparten
un `ToolContext` que acumula las fuentes y los nombres de herramientas usadas.
"""
from collections import Counter
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.tagging import categorize
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


# ─── CAMINO CON KEY: AGENTE ReAct ────────────────────────────────────────────

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


def _run_heuristic_router(question: str, ctx: ToolContext) -> str:
    q = question.lower()

    # 1. Escalar a RR.HH.
    if any(kw in q for kw in _ESCALAR_KW):
        return ctx.escalar_a_rrhh(question)

    # 2. Completar una tarea (el matching por solapamiento usa el texto completo)
    if "tarea" in q and any(kw in q for kw in _COMPLETAR_KW):
        return ctx.completar_tarea(question)

    # 3. Consultar tareas / progreso
    if any(w in q for w in ["mis tareas", "qué tareas", "que tareas", "pendiente",
                            "mi progreso", "qué me falta", "que me falta"]):
        return ctx.consultar_mis_tareas()

    # 4. Pregunta informativa → RAG + respuesta mock
    context = ctx.buscar_en_documentos(question)
    encontro_docs = bool(ctx.sources)
    return generate_mock_answer(question, context if encontro_docs else "")


def generate_mock_answer(question: str, context: str) -> str:
    q = question.lower()

    if context:
        return f"Basándome en los documentos de la empresa, encontré información relevante sobre tu consulta. {context[:300]}..."

    if "vacacion" in q:
        return "Para solicitar vacaciones debes ingresar al portal de RR.HH. con al menos 15 días de anticipación, diligenciar el formulario de solicitud y esperar aprobación de tu líder directo."
    elif "responsabilidad" in q or "rol" in q:
        return "Tus responsabilidades principales incluyen implementar features, escribir pruebas unitarias, participar en code reviews y documentar tus cambios según los estándares del equipo."
    elif "jira" in q:
        return "Para gestionar tickets en Jira: abre el ticket desde tu tablero y arrastra la tarjeta a la columna correspondiente o usa el botón de transición dentro del ticket."
    elif "salario" in q or "sueldo" in q:
        return "No tengo acceso a información sobre salarios en los documentos disponibles para tu perfil. Te recomiendo contactar directamente a RR.HH."
    else:
        return "Entiendo tu pregunta. Basándome en los documentos disponibles de la empresa puedo ayudarte. ¿Podrías ser más específico sobre lo que necesitas saber?"


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

    resolved_key = api_key or settings.OPENAI_API_KEY
    if not resolved_key:
        return fallback

    try:
        llm = ChatOpenAI(
            model=model,
            temperature=0.2,
            openai_api_key=resolved_key,
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

    # La clave de la empresa (configurada desde la UI) tiene prioridad sobre la del .env
    api_key = openai_api_key or settings.OPENAI_API_KEY

    if api_key:
        try:
            answer = _run_react_agent(
                question, ctx, history or [],
                api_key=api_key,
                model=ai_model,
                temperature=ai_temperature,
                agent_name=agent_name,
            )
        except Exception as e:
            print(f"Agente ReAct falló, usando router heurístico: {e}")
            answer = _run_heuristic_router(question, ctx)
    else:
        answer = _run_heuristic_router(question, ctx)

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
