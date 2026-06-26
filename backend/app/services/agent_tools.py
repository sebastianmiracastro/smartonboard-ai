"""Herramientas reales del agente de onboarding.

Cada herramienta es una función Python que opera de verdad sobre la base de datos
respetando el RBAC y el multi-tenant. La fábrica `build_tool_context` agrupa el
contexto de la petición (sesión de BD, datos del usuario y acumuladores) y
`build_langchain_tools` envuelve esas funciones como StructuredTools para que el
agente ReAct (con OPENAI_API_KEY) pueda invocarlas vía function-calling.

El camino sin key (router heurístico en agent.py) llama estas mismas funciones
directamente a través de `ToolContext`, de modo que las herramientas son
demostrables aunque no haya LLM.
"""
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.models import EmployeeTask, EmployeePlan, Document, RRHHAlert
from app.services.rag import deep_retrieve, build_rich_context, RetrievedChunk
from app.services.tagging import categorize


# Nombres canónicos de las herramientas (también se persisten en tools_used)
TOOL_BUSCAR = "buscar_en_documentos"
TOOL_CONSULTAR_TAREAS = "consultar_mis_tareas"
TOOL_COMPLETAR_TAREA = "completar_tarea"
TOOL_ESCALAR_RRHH = "escalar_a_rrhh"

# Palabras vacías/de comando que no aportan a la identificación de una tarea
_STOPWORDS = {
    "tarea", "tareas", "marca", "marcar", "marcala", "completa", "completar",
    "completada", "completado", "como", "ya", "termine", "terminé", "termino",
    "finalice", "finalicé", "hice", "esta", "este", "una", "uno", "que", "del",
    "los", "las", "por", "favor", "quiero", "necesito", "puedes", "podrias",
    "podrías", "para", "con", "mis", "mi",
}


def _normalize(text: str) -> str:
    """minúsculas sin acentos."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _significant_words(text: str) -> set:
    return {w for w in _normalize(text).replace(",", " ").split()
            if len(w) >= 3 and w not in _STOPWORDS}


@dataclass
class ToolContext:
    """Contexto compartido entre las herramientas durante una petición."""
    db: Session
    user_id: str
    company_id: str
    user_is_rrhh: bool = False
    user_is_gerencia: bool = False
    user_seniority_level: int = 1
    user_department_id: Optional[str] = None
    user_role_id: Optional[str] = None
    rag_top_k: int = 5
    # Acumuladores que el orquestador lee después de ejecutar las tools
    sources: List[dict] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    # Fragmentos recuperados en la última búsqueda (los usa el sintetizador extractivo)
    retrieved_chunks: List[RetrievedChunk] = field(default_factory=list)
    # Señales para las métricas de conocimiento (las llena buscar_en_documentos)
    matched_categories: List[str] = field(default_factory=list)
    answer_confidence: float = 0.0

    def _mark(self, tool_name: str) -> None:
        if tool_name not in self.tools_used:
            self.tools_used.append(tool_name)

    # ─── Herramientas ────────────────────────────────────────────────────────

    def buscar_en_documentos(self, consulta: str, queries: Optional[List[str]] = None) -> str:
        """Investiga a FONDO en los documentos accesibles (respeta RBAC).

        No se queda con la primera coincidencia: usa `deep_retrieve` con varias
        reformulaciones de la pregunta (`queries`), trae fragmentos vecinos para no
        cortar ideas y ensambla un contexto completo y legible. Pensado para que el
        LLM reorganice esos fragmentos en una respuesta sin brechas.
        """
        self._mark(TOOL_BUSCAR)
        # Consultas a lanzar: la original + sus reformulaciones (si las hay)
        all_queries = [consulta] + [q for q in (queries or []) if q and q.strip()]
        # Profundidad de la búsqueda: generosa por diseño (completitud > tokens)
        max_chunks = max(12, self.rag_top_k * 4)
        chunks = deep_retrieve(
            db=self.db,
            company_id=self.company_id,
            queries=all_queries,
            user_is_rrhh=self.user_is_rrhh,
            user_is_gerencia=self.user_is_gerencia,
            user_seniority_level=self.user_seniority_level,
            user_department_id=self.user_department_id,
            user_role_id=self.user_role_id,
            max_chunks=max_chunks,
            neighbor_radius=1,
            prefer_category=categorize(consulta),  # prioriza el tema de la pregunta
        )
        # Guardar los fragmentos para el sintetizador extractivo (camino sin clave de IA)
        self.retrieved_chunks = chunks

        if not chunks:
            return "No encontré información sobre eso en los documentos disponibles para tu perfil."

        # Señales para métricas: categorías reales de los chunks relevantes (no los
        # vecinos de relleno) y mejor similitud alcanzada.
        self.matched_categories.extend(
            c.category for c in chunks if c.category and not c.is_neighbor
        )
        top_sim = max((c.similarity for c in chunks), default=0.0)
        self.answer_confidence = max(self.answer_confidence, top_sim)

        # Registrar las fuentes (documentos) para mostrarlas en el chat
        doc_ids = list({c.document_id for c in chunks})
        docs = self.db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_names = {d.id: d.name for d in docs}
        for doc_id in doc_ids:
            src = {"id": doc_id, "name": doc_names.get(doc_id, doc_id)}
            if src not in self.sources:
                self.sources.append(src)

        return build_rich_context(chunks, doc_names=doc_names)

    def _lost_plan_ids(self) -> set:
        """Ids de planes 'perdidos' del empleado (sus pasos ya no cuentan)."""
        return {
            ep.id for ep in self.db.query(EmployeePlan).filter(
                EmployeePlan.user_id == self.user_id,
                EmployeePlan.status == "perdido",
            ).all()
        }

    def consultar_mis_tareas(self) -> str:
        """Devuelve la lista de pasos del plan vigente del empleado con su estado."""
        self._mark(TOOL_CONSULTAR_TAREAS)
        lost = self._lost_plan_ids()
        tasks = [
            t for t in self.db.query(EmployeeTask)
            .filter(EmployeeTask.user_id == self.user_id)
            .order_by(EmployeeTask.order_index, EmployeeTask.day_number)
            .all()
            if t.employee_plan_id not in lost
        ]
        if not tasks:
            return "Todavía no tienes tareas de onboarding asignadas."

        estado = {"pendiente": "sin empezar", "en_progreso": "en progreso", "completada": "completada"}
        lineas = []
        for t in tasks:
            dia = f"Día {t.day_number}" if t.day_number else "Sin día"
            tipo = " (cuestionario)" if t.category == "cuestionario" else ""
            lineas.append(f"- [{estado.get(t.status, t.status)}] {t.title}{tipo} ({dia})")
        return "Tus pasos de onboarding:\n" + "\n".join(lineas)

    def completar_tarea(self, titulo: str) -> str:
        """Marca como completada una tarea del empleado identificada por su título
        (coincidencia parcial, sin distinguir mayúsculas)."""
        self._mark(TOOL_COMPLETAR_TAREA)
        from datetime import datetime
        from app.services.onboarding import accumulate_step_time, check_plan_completion

        lost = self._lost_plan_ids()
        pendientes = [
            t for t in self.db.query(EmployeeTask)
            .filter(
                EmployeeTask.user_id == self.user_id,
                EmployeeTask.status != "completada",
            ).all()
            # los cuestionarios se aprueban respondiendo, no se "marcan" por chat
            if t.employee_plan_id not in lost and t.category != "cuestionario"
        ]
        if not pendientes:
            return (
                "No tienes pasos pendientes por marcar. Si tienes un cuestionario, "
                "debes responderlo desde 'Mi plan' en el portal."
            )

        disponibles = ", ".join(f"'{t.title}'" for t in pendientes)
        query_words = _significant_words(titulo)

        # Coincidencia por solapamiento de palabras significativas (robusto al
        # lenguaje natural y a los acentos). Se elige la tarea con más palabras
        # del título presentes en el texto del usuario.
        puntuadas = []
        for t in pendientes:
            score = len(_significant_words(t.title) & query_words)
            if score > 0:
                puntuadas.append((score, t))

        if not puntuadas:
            return (
                f"No encontré una tarea pendiente que coincida con lo que dijiste. "
                f"Tus tareas pendientes son: {disponibles}."
            )

        mejor = max(s for s, _ in puntuadas)
        empatadas = [t for s, t in puntuadas if s == mejor]
        if len(empatadas) > 1:
            opciones = ", ".join(f"'{t.title}'" for t in empatadas)
            return (
                f"¿Cuál de estas quieres marcar como completada?: {opciones}."
            )

        tarea = empatadas[0]
        accumulate_step_time(tarea)
        tarea.status = "completada"
        tarea.completed_at = datetime.utcnow()
        # Si era el último paso del plan, márcalo como finalizado
        if tarea.employee_plan_id:
            ep = self.db.query(EmployeePlan).filter(EmployeePlan.id == tarea.employee_plan_id).first()
            if ep:
                check_plan_completion(self.db, ep)
        self.db.commit()
        return f"Listo, marqué como completada la tarea '{tarea.title}'. ¡Bien hecho! 🎉"

    def escalar_a_rrhh(self, motivo: str) -> str:
        """Crea una alerta para que el área de RR.HH. acompañe al empleado."""
        self._mark(TOOL_ESCALAR_RRHH)
        alerta = RRHHAlert(
            company_id=self.company_id,
            user_id=self.user_id,
            motivo=(motivo or "El empleado solicitó acompañamiento de RR.HH.").strip(),
        )
        self.db.add(alerta)
        self.db.commit()
        return (
            "He notificado a RR.HH. para que te acompañen con esto. "
            "Se pondrán en contacto contigo pronto."
        )


def build_langchain_tools(ctx: ToolContext) -> list:
    """Envuelve las herramientas del contexto como StructuredTools de LangChain
    para el agente ReAct (camino con OPENAI_API_KEY)."""
    from langchain_core.tools import tool

    @tool
    def buscar_en_documentos(consulta: str) -> str:
        """Busca información en los documentos internos de la empresa (políticas,
        guías, procesos). Úsala cuando el empleado pregunte por información que
        podría estar documentada."""
        return ctx.buscar_en_documentos(consulta)

    @tool
    def consultar_mis_tareas() -> str:
        """Consulta las tareas de onboarding del empleado y su estado. Úsala
        cuando pregunte por sus tareas, pendientes o progreso."""
        return ctx.consultar_mis_tareas()

    @tool
    def completar_tarea(titulo: str) -> str:
        """Marca como completada una tarea de onboarding del empleado, dada por su
        título o parte de él. Úsala cuando el empleado diga que terminó algo."""
        return ctx.completar_tarea(titulo)

    @tool
    def escalar_a_rrhh(motivo: str) -> str:
        """Notifica a RR.HH. para que acompañen al empleado. Úsala cuando esté
        bloqueado, frustrado o pida ayuda humana."""
        return ctx.escalar_a_rrhh(motivo)

    return [buscar_en_documentos, consultar_mis_tareas, completar_tarea, escalar_a_rrhh]
