from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from sqlalchemy.orm import Session
from app.services.rag import search_similar_chunks, build_context
from app.models.models import Document
from app.core.config import settings
import json

# ─── ESTADO DEL AGENTE ───────────────────────────────────────────────────────

class AgentState(TypedDict):
    question: str
    context: str
    answer: str
    sources: List[dict]
    category: str
    depth_level: str
    history: List[dict]
    company_id: str
    user_is_rrhh: bool
    user_is_gerencia: bool
    user_seniority_level: int
    user_department_id: Optional[str]
    db: object

# ─── NODOS DEL GRAFO ─────────────────────────────────────────────────────────

def retrieve_context(state: AgentState) -> AgentState:
    db = state["db"]
    chunks = search_similar_chunks(
        db=db,
        company_id=state["company_id"],
        query=state["question"],
        user_is_rrhh=state["user_is_rrhh"],
        user_is_gerencia=state["user_is_gerencia"],
        user_seniority_level=state["user_seniority_level"],
        user_department_id=state["user_department_id"],
        top_k=5
    )
    context = build_context(chunks)
    doc_ids = list(set([doc_id for _, doc_id, _ in chunks]))
    doc_names = {}
    if doc_ids:
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_names = {d.id: d.name for d in docs}
    sources = [{"id": doc_id, "name": doc_names.get(doc_id, doc_id)} for doc_id in doc_ids]
    return {**state, "context": context, "sources": sources}

def classify_question(state: AgentState) -> AgentState:
    question = state["question"].lower()

    # Categoría
    if any(w in question for w in ["proceso", "procedimiento", "cómo funciona", "pasos"]):
        category = "procesos"
    elif any(w in question for w in ["responsabilidad", "función", "rol", "cargo", "debo hacer"]):
        category = "rol"
    elif any(w in question for w in ["política", "norma", "beneficio", "vacacion", "permiso"]):
        category = "cultura"
    elif any(w in question for w in ["jira", "slack", "git", "herramienta", "sistema", "configurar"]):
        category = "herramientas"
    elif any(w in question for w in ["quién", "equipo", "reporto", "líder", "compañero"]):
        category = "relaciones"
    else:
        category = "procesos"

    # Profundidad
    words = question.split()
    if len(words) <= 5:
        depth = "basico"
    elif len(words) <= 12:
        depth = "intermedio"
    else:
        depth = "avanzado"

    return {**state, "category": category, "depth_level": depth}

SYSTEM_PROMPT = """Eres Sara, la asistente virtual de onboarding de la empresa.
Acompañas a los nuevos empleados durante sus primeras semanas y haces que se
sientan bienvenidos y orientados.

Tu estilo:
- Cálida, cercana y profesional. Hablas en español de forma natural, como una
  compañera que de verdad quiere ayudar, no como un robot que recita.
- Conversacional: tienes en cuenta lo que ya se habló antes en la conversación
  y le das continuidad sin repetir lo obvio.
- Concreta y útil: cuando aplica, das pasos claros y ordenados, sin rodeos.
- Empática: si la persona está perdida o abrumada, la tranquilizas.

Cómo usar la información:
- Cuando en el contexto haya fragmentos de los documentos de la empresa, basa tu
  respuesta en ellos y menciónalos con naturalidad ("según la guía de...", etc.).
- Si la pregunta es sobre algo específico de la empresa y no hay información en
  los documentos, dilo con honestidad y sugiere a quién acudir (por ejemplo,
  RR.HH. o su líder directo). Nunca inventes políticas, cifras, nombres ni fechas.
- Para preguntas generales de onboarding, dudas de bienvenida o conversación
  casual (saludos, agradecimientos), responde con tu propio criterio de forma
  amable y humana, aunque no haya documentos.
- Mantén las respuestas enfocadas: ni demasiado cortas ni un muro de texto."""


def generate_answer(state: AgentState) -> AgentState:
    # Si no hay API key usamos respuesta mock
    if not settings.OPENAI_API_KEY:
        answer = generate_mock_answer(state["question"], state["context"])
        return {**state, "answer": answer}

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.6,
            openai_api_key=settings.OPENAI_API_KEY
        )

        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        # Memoria conversacional: últimos turnos de la conversación
        for h in (state.get("history") or [])[-10:]:
            if h.get("role") == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h.get("role") == "assistant":
                messages.append(AIMessage(content=h["content"]))

        context = state["context"] if state["context"] else "No hay fragmentos de documentos relevantes para esta pregunta."
        messages.append(HumanMessage(content=f"""Contexto de documentos de la empresa (puede estar vacío):
\"\"\"
{context}
\"\"\"

Pregunta del empleado: {state["question"]}

Responde de forma natural, cálida y útil siguiendo tu estilo."""))

        response = llm.invoke(messages)
        answer = response.content

    except Exception as e:
        answer = generate_mock_answer(state["question"], state["context"])

    return {**state, "answer": answer}

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

def generate_title(question: str, answer: str = "") -> str:
    """Genera un título corto que resume el tema de la conversación."""
    fallback = (question or "").strip()
    if len(fallback) > 45:
        fallback = fallback[:45].rsplit(" ", 1)[0] + "…"
    fallback = fallback or "Nueva conversación"

    if not settings.OPENAI_API_KEY:
        return fallback

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            openai_api_key=settings.OPENAI_API_KEY,
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

# ─── CONSTRUIR GRAFO ─────────────────────────────────────────────────────────

def build_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve", retrieve_context)
    workflow.add_node("classify", classify_question)
    workflow.add_node("answer", generate_answer)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "classify")
    workflow.add_edge("classify", "answer")
    workflow.add_edge("answer", END)

    return workflow.compile()

agent = build_agent()

# ─── FUNCIÓN PRINCIPAL ───────────────────────────────────────────────────────

def run_agent(
    question: str,
    company_id: str,
    db: Session,
    user_is_rrhh: bool = False,
    user_is_gerencia: bool = False,
    user_seniority_level: int = 1,
    user_department_id: Optional[str] = None,
    history: Optional[List[dict]] = None,
) -> dict:
    result = agent.invoke({
        "question": question,
        "context": "",
        "answer": "",
        "sources": [],
        "category": "",
        "depth_level": "",
        "history": history or [],
        "company_id": company_id,
        "user_is_rrhh": user_is_rrhh,
        "user_is_gerencia": user_is_gerencia,
        "user_seniority_level": user_seniority_level,
        "user_department_id": user_department_id,
        "db": db,
    })

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "category": result["category"],
        "depth_level": result["depth_level"],
    }