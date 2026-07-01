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
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.models import (
    EmployeeTask, EmployeePlan, Document, RRHHAlert, User, Conversation, ChatMessage,
)
from app.services.rag import deep_retrieve, build_rich_context, RetrievedChunk
from app.services.tagging import categorize


# Nombres canónicos de las herramientas (también se persisten en tools_used)
TOOL_BUSCAR = "buscar_en_documentos"
TOOL_CONSULTAR_TAREAS = "consultar_mis_tareas"
TOOL_COMPLETAR_TAREA = "completar_tarea"
TOOL_ESCALAR_RRHH = "escalar_a_rrhh"
TOOL_PERFIL = "consultar_mi_perfil"

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


def profile_topic(question: str) -> Optional[str]:
    """Detecta (sin LLM) si la pregunta es sobre los DATOS DE PERFIL del propio
    usuario en la plataforma, y de qué subtema. Devuelve el subtema o None.

    Estos datos viven en la BD (no en documentos): plan asignado, nivel de
    comprensión, documentos accesibles/exclusivos/generales, cargo/área/estado.
    """
    q = _normalize(question)
    # Nivel de comprensión / entendimiento del propio usuario
    if any(k in q for k in ["entendimiento", "entiendo", "comprension", "comprend",
                            "mi nivel", "mi puntaje", "mi score", "mi porcentaje",
                            "mi calificacion", "que tan bien voy", "que tanto se"]):
        return "comprension"
    # Documentos/recursos accesibles a MI perfil (exige nombre + matiz personal)
    if any(k in q for k in ["documento", "documentos", "archivo", "archivos",
                            "recurso", "recursos", "material"]) and \
       any(k in q for k in ["teng", "mis ", "mi ", "puedo ver", "accesibl", "disponibl",
                            "exclusiv", "general", "cargad", "acceso", "asignad", "perfil"]):
        return "documentos"
    # Plan de onboarding asignado
    if "plan" in q and any(k in q for k in ["teng", "algun", "asignad", "hay",
                                            "mi plan", "cuento con"]):
        return "plan"
    # Datos personales del perfil / avance de onboarding
    if any(k in q for k in ["mi cargo", "mi rol", "mi puesto", "mi departamento",
                            "mi area", "mi perfil", "mi informacion", "mi estado",
                            "dia de onboarding", "dia voy", "cuanto llevo",
                            "mi antiguedad", "quien soy"]):
        return "perfil"
    return None


# Vocabulario social: se compara contra el mensaje LIMPIO y CORTO, para no confundir
# un saludo con una consulta real (p. ej. "hola, cómo pido vacaciones" NO es social).
_SOCIAL = {
    "saludo": {"hola", "hola buenas", "buenas", "buenos dias", "buenas tardes",
               "buenas noches", "hey", "que tal", "que mas", "holi", "saludos",
               "hola que tal", "ey"},
    "gracias": {"gracias", "muchas gracias", "mil gracias", "te agradezco",
                "perfecto gracias", "listo gracias", "vale gracias", "ok gracias",
                "muy amable", "excelente gracias", "genial gracias", "gracias totales"},
    "despedida": {"adios", "chao", "hasta luego", "nos vemos", "hasta pronto", "bye",
                  "hasta manana", "me voy", "chau", "hasta la proxima"},
    "como_estas": {"como estas", "como vas", "como te va", "todo bien", "que hay"},
}
# Muletillas que se ignoran al normalizar (incluye el nombre por defecto del agente).
_SOCIAL_FILLER = {"por", "favor", "muy", "el", "la", "y", "a", "sara", "porfa", "pues"}


def social_intent(question: str) -> Optional[str]:
    """Detecta saludos, agradecimientos y despedidas cuando el mensaje es
    ESENCIALMENTE social (corto y sin una consulta real). Devuelve la categoría o None."""
    q = re.sub(r"[^a-z0-9ñ ]", " ", _normalize(question))
    words = [w for w in q.split() if w not in _SOCIAL_FILLER]
    if not words or len(words) > 4:
        return None
    cleaned = " ".join(words)
    for categoria, frases in _SOCIAL.items():
        if cleaned in frases:
            return categoria
    return None


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

    def consultar_mi_perfil(self, pregunta: str) -> str:
        """Responde preguntas sobre los datos de perfil del usuario en la plataforma
        (plan asignado, comprensión, documentos accesibles, cargo/área). Toda la
        información sale de la BD respetando el perfil de quien pregunta."""
        self._mark(TOOL_PERFIL)
        topic = profile_topic(pregunta) or "perfil"
        if topic == "documentos":
            return self._perfil_documentos(_normalize(pregunta))
        if topic == "comprension":
            return self._perfil_comprension()
        if topic == "plan":
            return self._perfil_plan()
        return self._perfil_general()

    def _perfil_plan(self) -> str:
        from app.services.onboarding import ACTIVE_PLAN_STATES
        ep = (
            self.db.query(EmployeePlan)
            .filter(EmployeePlan.user_id == self.user_id,
                    EmployeePlan.status.in_(ACTIVE_PLAN_STATES))
            .order_by(EmployeePlan.assigned_at.desc())
            .first()
        )
        if not ep:
            return (
                "Ahora mismo no tienes ningún plan de onboarding asignado. Cuando "
                "RR.HH. te asigne uno, aparecerá en 'Mi plan' y te avisaré."
            )
        steps = self.db.query(EmployeeTask).filter(
            EmployeeTask.employee_plan_id == ep.id
        ).all()
        total = len(steps)
        done = sum(1 for s in steps if s.status == "completada")
        pct = round(done / total * 100) if total else 0
        estado = {"sin_empezar": "sin empezar", "en_progreso": "en progreso",
                  "finalizado": "finalizado"}.get(ep.status, ep.status)
        msg = (
            f"Sí, tienes asignado el plan «{ep.plan_name}» ({estado}). "
            f"Llevas {done} de {total} pasos completados ({pct}%)."
        )
        if ep.score is not None:
            msg += f" Nota del plan: {ep.score:.0f}/100."
        return msg

    def _perfil_comprension(self) -> str:
        # Reutiliza la métrica central de RR.HH.: overall + desglose por categoría.
        from app.services.evaluation import compute_knowledge_metrics
        user = self.db.query(User).filter(User.id == self.user_id).first()
        metrics = compute_knowledge_metrics(self.db, user)
        cats = [c for c in metrics["by_category"] if c["comprehension"] is not None]
        if not cats:
            return (
                "Todavía no tengo suficientes interacciones tuyas para estimar tu "
                "nivel de comprensión. A medida que me hagas preguntas, lo iré midiendo."
            )
        total_q = sum(c["questions"] for c in cats)
        overall = sum(c["comprehension"] * c["questions"] for c in cats) / total_q
        pct = round(overall * 100)
        nivel = "alto" if pct >= 75 else "medio" if pct >= 50 else "en construcción"
        # Desglose por tema, del más flojo al más fuerte (para que sepas dónde reforzar).
        detalle = ", ".join(
            f"{c['category']} {round(c['comprehension'] * 100)}%"
            for c in sorted(cats, key=lambda x: x["comprehension"])
        )
        msg = (
            f"Tu nivel de comprensión estimado es del {pct}% (nivel {nivel}), sobre "
            f"{total_q} interacción(es). Por tema: {detalle}."
        )
        flojos = [c["category"] for c in cats if c["status"] in ("refuerzo", "perdida")]
        if flojos:
            msg += f" Te conviene reforzar: {', '.join(flojos)}."
        return msg

    def _perfil_documentos(self, q: str) -> str:
        from app.services.rag import accessible_document_ids
        ids = accessible_document_ids(
            self.db, self.company_id, self.user_is_rrhh, self.user_is_gerencia,
            self.user_seniority_level, self.user_department_id, self.user_role_id,
        )
        if not ids:
            return (
                "Por ahora no tienes documentos disponibles para tu perfil. Cuando "
                "RR.HH. suba material para tu área o cargo, aparecerá en Recursos."
            )
        docs = self.db.query(Document).filter(Document.id.in_(ids)).all()

        def es_exclusivo(d: Document) -> bool:
            # 'Exclusivo' = tiene alguna restricción de acceso (no es para todos).
            return bool(
                d.dept_permission or d.role_permission or d.require_rrhh
                or d.require_gerencia or (d.min_seniority and d.min_seniority > 1)
            )

        exclusivos = [d for d in docs if es_exclusivo(d)]
        generales = [d for d in docs if not es_exclusivo(d)]

        if "exclusiv" in q:
            if exclusivos:
                nombres = ", ".join(f"«{d.name}»" for d in exclusivos)
                return (
                    f"Sí, tienes {len(exclusivos)} documento(s) exclusivo(s) de tu "
                    f"perfil (por tu cargo, área o nivel): {nombres}."
                )
            return (
                "No tienes documentos exclusivos de tu perfil; los que ves son de "
                "acceso general para la empresa."
            )
        if "general" in q:
            if generales:
                nombres = ", ".join(f"«{d.name}»" for d in generales)
                return f"Sí, tienes {len(generales)} documento(s) de acceso general: {nombres}."
            return (
                "No tienes documentos de acceso general por ahora; los que ves son "
                "específicos de tu perfil."
            )

        lineas = [f"- «{d.name}» ({'exclusivo' if es_exclusivo(d) else 'general'})" for d in docs]
        return (
            f"Tienes acceso a {len(docs)} documento(s) según tu perfil "
            f"({len(exclusivos)} exclusivo(s), {len(generales)} general(es)):\n"
            + "\n".join(lineas)
        )

    def _perfil_general(self) -> str:
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user:
            return "No pude cargar tu información de perfil."
        partes = [f"Eres {user.full_name}"]
        if user.role_name:
            partes.append(f"cargo {user.role_name}")
        if user.department_name:
            partes.append(f"área {user.department_name}")
        estado = {"onboarding": "en onboarding", "activo": "activo"}.get(user.status, user.status)
        msg = ", ".join(partes) + f". Estado: {estado}."
        if user.status == "onboarding" and user.onboarding_total_days:
            msg += (
                f" Vas en el día {user.onboarding_day} de {user.onboarding_total_days} "
                "de tu incorporación."
            )
        return msg

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
    def consultar_mi_perfil(pregunta: str) -> str:
        """Consulta los datos de PERFIL del empleado en la plataforma: si tiene un
        plan asignado, su nivel de comprensión, y los documentos accesibles para su
        perfil (exclusivos o generales). Úsala cuando pregunte por su propia
        información en la plataforma, no por el contenido de los documentos."""
        return ctx.consultar_mi_perfil(pregunta)

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

    return [buscar_en_documentos, consultar_mis_tareas, consultar_mi_perfil,
            completar_tarea, escalar_a_rrhh]
