from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session
from app.services.rag import search_similar_chunks, build_context
from app.core.config import settings
import json

# ─── ESTADO DEL AGENTE ───────────────────────────────────────────────────────

class AgentState(TypedDict):
    question: str
    context: str
    answer: str
    sources: List[str]
    category: str
    depth_level: str
    company_id: str
    user_is_rrhh: bool
    user_is_gerencia: bool
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
        top_k=5
    )
    context = build_context(chunks)
    sources = list(set([doc_id for _, doc_id, _ in chunks]))
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

def generate_answer(state: AgentState) -> AgentState:
    # Si no hay API key usamos respuesta mock
    if not settings.OPENAI_API_KEY:
        answer = generate_mock_answer(state["question"], state["context"])
        return {**state, "answer": answer}

    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY
        )

        system_prompt = """Eres un asistente de onboarding empresarial.
Tu trabajo es ayudar a los nuevos empleados respondiendo sus preguntas
basándote ÚNICAMENTE en la información de los documentos de la empresa.

Reglas:
- Responde siempre en español
- Si la información no está en los documentos, dilo claramente
- Sé conciso y directo
- No inventes información
- Si hay información relevante, cítala naturalmente"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
Contexto de documentos:
{state["context"] if state["context"] else "No hay documentos disponibles sobre este tema."}

Pregunta del empleado: {state["question"]}

Responde de forma clara y útil.""")
        ]

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
    user_is_gerencia: bool = False
) -> dict:
    result = agent.invoke({
        "question": question,
        "context": "",
        "answer": "",
        "sources": [],
        "category": "",
        "depth_level": "",
        "company_id": company_id,
        "user_is_rrhh": user_is_rrhh,
        "user_is_gerencia": user_is_gerencia,
        "db": db,
    })

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "category": result["category"],
        "depth_level": result["depth_level"],
    }