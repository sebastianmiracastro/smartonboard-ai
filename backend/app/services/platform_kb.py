"""Conocimiento propio de SmartOnboard AI (auto-conocimiento del producto).

El agente responde con RAG sobre los documentos que sube CADA empresa. Pero si
un empleado pregunta por la plataforma en sí —qué es, para qué sirve, cuál es su
alcance, qué modelo de IA usa, cómo funciona— eso NO está en esos documentos.

Este módulo aporta ese conocimiento de forma nativa, tomado del informe de trabajo
de grado (SmartOnBoard_AI.pdf), sin depender de que nadie suba documentación:

- `is_platform_question()` detecta (sin LLM) si la pregunta es sobre la plataforma.
- `answer_platform_question()` responde:
    · Con clave de IA: el LLM redacta a partir de esta base de conocimiento.
    · SIN clave (nuestro modelo de la casa): se enruta la pregunta al ASPECTO que
      pide (qué es, objetivo, alcance, modelo, cómo funciona, resultados, autor…)
      y se devuelve su párrafo curado completo. Responde puntualmente, siempre da
      en el blanco y nunca queda cortado a media frase.
"""
import random
from typing import List, Optional


PLATFORM_NAME = "SmartOnboard AI"

# ─── BASE DE CONOCIMIENTO POR ASPECTOS ───────────────────────────────────────
# Cada aspecto es un párrafo curado, autocontenido y verificado contra el informe.
# La pregunta selecciona el/los aspecto(s) pertinente(s): respuesta puntual y sin
# recortes (se devuelve el párrafo entero, no un truncado por caracteres).

ASPECTS = {
    "identidad": (
        "SmartOnboard AI es una plataforma web inteligente de onboarding empresarial que "
        "automatiza y personaliza la incorporación de nuevos empleados. Funciona como software "
        "como servicio (SaaS) multiempresa —cada organización tiene su propio espacio de "
        "conocimiento aislado— y es el proyecto de grado de Ingeniería de Software de Sebastián "
        "Mira Castro en el Politécnico Grancolombiano (2026). Como asistente, respondo tus "
        "preguntas en lenguaje natural con base en la documentación de tu empresa, te muestro tus "
        "tareas de onboarding y ayudo a que Recursos Humanos siga tu progreso."
    ),
    "capacidades": (
        "Puedo ayudarte a: resolver dudas sobre las políticas, procesos y documentos de tu empresa "
        "—respondiendo con base en ellos y citando la fuente—, mostrarte tus tareas de onboarding y "
        "marcarlas como completadas, y escalar tu caso a Recursos Humanos cuando necesites ayuda de "
        "una persona. Pregúntame lo que necesites de tu incorporación."
    ),
    "objetivo": (
        "El objetivo de SmartOnboard AI es reducir el tiempo de incorporación efectiva de los "
        "empleados nuevos y darle a Recursos Humanos métricas objetivas para evaluar el proceso. "
        "Ataca tres problemas del onboarding tradicional: la información dispersa y sin buscador "
        "semántico, la dependencia de RR.HH. para resolver preguntas repetitivas, y la falta de una "
        "forma objetiva de medir el avance del empleado en sus primeras semanas."
    ),
    "alcance": (
        "El alcance de la plataforma cubre la gestión de documentos, los planes de onboarding con "
        "tareas, el chat con el asistente de IA, el seguimiento de tareas del empleado y las métricas "
        "de progreso y comprensión para RR.HH. Todo con control de acceso (RBAC) en tres niveles "
        "combinables —por departamento, por antigüedad del cargo y por banderas de RR.HH./gerencia—, "
        "aplicado antes de la búsqueda, de modo que el asistente nunca ve documentos a los que no "
        "tienes permiso. Su arquitectura es multiempresa (multi-tenant)."
    ),
    "funcionamiento": (
        "Funciona con generación aumentada por recuperación (RAG). Cuando RR.HH. sube un documento, "
        "la plataforma extrae el texto, lo divide en fragmentos y genera un embedding (representación "
        "semántica) de cada uno. Cuando preguntas, filtra por tus permisos, busca por similitud los "
        "fragmentos más relevantes, recupera los cinco mejores y con ese contexto el agente redacta "
        "la respuesta citando de qué documento salió. El agente está construido con LangGraph (patrón "
        "ReAct) como un grafo de tres pasos —recuperar, clasificar y generar— y clasifica cada "
        "consulta en cinco categorías y tres niveles de profundidad. Si no hay información, lo dice "
        "con honestidad en vez de inventar."
    ),
    "modelo": (
        "Para los embeddings uso el modelo all-MiniLM-L6-v2 de sentence-transformers (local y "
        "gratuito). Para redactar la respuesta: si la empresa configura su clave de OpenAI uso un "
        "modelo como GPT-4o mini; si no hay clave, un sintetizador extractivo propio arma la respuesta "
        "100% offline. Además, el proyecto especializa un modelo de lenguaje de código abierto "
        "(TinyLlama-1.1B) con ajuste fino LoRA (rango 16, alfa 32) y cuantización de cuatro bits "
        "(QLoRA), entrenado en Google Colab con GPU T4; la comparativa frente al modelo base mostró "
        "una mejora medible. La calidad se evalúa automáticamente con métricas tipo RAGAS: fidelidad "
        "(40%), relevancia de la respuesta (40%) y precisión del contexto (20%)."
    ),
    "tecnologia": (
        "La arquitectura técnica es: backend en FastAPI (Python) con base de datos PostgreSQL, "
        "frontend en Next.js con TailwindCSS, y todo el sistema corre en contenedores Docker. La API "
        "REST usa autenticación JWT y arquitectura multiempresa. La IA se apoya en LangGraph para el "
        "agente, sentence-transformers para los embeddings y, opcionalmente, OpenAI para la redacción."
    ),
    "roles": (
        "Recursos Humanos (o gerencia) administra la plataforma: sube documentos, define departamentos "
        "y cargos, crea planes de onboarding y revisa las métricas. El empleado nuevo usa el portal "
        "para chatear conmigo, ver sus tareas y consultar los recursos disponibles para su perfil."
    ),
    "resultados": (
        "En el escenario de demostración, la plataforma redujo el tiempo de incorporación efectiva de "
        "6,3 a 4,2 días en promedio y logró resolver automáticamente más del 90% de las consultas, "
        "liberando horas de RR.HH. Su arquitectura multiempresa la habilita como producto SaaS más "
        "allá del contexto académico."
    ),
    "estado": (
        "El desarrollo avanza por fases: el backend y el pipeline RAG (Fase 1) y el agente con el "
        "frontend (Fase 2) están completados; la evaluación automática y el ajuste fino del modelo "
        "(Fase 3) están en ejecución; y el cierre, las pruebas y la sustentación (Fase 4) quedan "
        "pendientes."
    ),
    "autor": (
        "SmartOnboard AI es el proyecto de grado de Sebastián Mira Castro, estudiante del Politécnico "
        "Grancolombiano (Bogotá, Colombia), presentado en 2026 como trabajo de grado de Ingeniería de "
        "Software."
    ),
    "integraciones": (
        "SmartOnboard AI sincroniza las tareas de onboarding con Jira, de modo que un paso puede "
        "reflejar su estado desde el tablero de la empresa. Como trabajo futuro se contemplan la "
        "integración con Google Calendar para agendar tareas y las notificaciones por correo "
        "(por ejemplo con SendGrid)."
    ),
    "seguridad": (
        "La seguridad se apoya en tres pilares: control de acceso por roles (RBAC), que filtra la "
        "información antes de la búsqueda para que nunca veas documentos sin permiso; aislamiento de "
        "los datos por empresa (multi-tenant); y autenticación con JWT. Además, el proyecto considera "
        "la Ley 1581 de 2012 de protección de datos personales de Colombia, con sus principios de "
        "finalidad, acceso restringido y seguridad de la información."
    ),
    "roadmap": (
        "Trabajo futuro previsto: usar el tipo vector nativo de pgvector, integración real con Jira y "
        "Google Calendar, notificaciones por correo, alertas automáticas a RR.HH. cuando baja la "
        "comprensión de un empleado, y fine-tuning continuo del modelo con las conversaciones reales."
    ),
}

# Respaldo de identidad y contexto completo para el camino con LLM.
OVERVIEW = ASPECTS["identidad"]
FULL_CONTEXT = "\n\n".join(ASPECTS.values())


# ─── DETECCIÓN (sin LLM) ─────────────────────────────────────────────────────

# Nombre explícito del producto: cualquier variante dispara con seguridad.
_NAME_TOKENS = ["smartonboard", "smart onboard", "smart-onboard"]

# Demostrativos ("esta plataforma…"): inequívocos, se refieren a la app actual, así
# que cualquier pregunta que los use se considera sobre la plataforma.
_SELF_TOKENS = [
    "esta plataforma", "este sistema", "esta aplicación", "esta aplicacion",
    "esta app", "esta herramienta", "este software", "este producto",
    "esta web", "este portal", "este servicio", "esta ia", "esta inteligencia",
    "este asistente", "este agente", "este chatbot", "este bot",
]

# Artículo definido ("la plataforma"): más ambiguo (puede ser un sistema interno
# de la empresa, "la plataforma de nómina"); solo cuenta si NO lleva "de …" detrás.
_WEAK_SELF_TOKENS = ["la plataforma", "el asistente", "el sistema"]

# Identidad/capacidad del propio asistente o su modelo de IA: por sí solas bastan.
_IDENTITY_PHRASES = [
    "quién eres", "quien eres", "qué eres", "que eres", "cómo te llamas",
    "como te llamas", "para qué sirves", "para que sirves", "qué haces",
    "que haces", "qué puedes hacer", "que puedes hacer", "en qué me puedes ayudar",
    "en que me puedes ayudar", "en qué me ayudas", "en que me ayudas",
    "para qué me sirves", "para que me sirves", "qué eres tú", "que eres tu",
    "cómo funcionas", "como funcionas", "cómo trabajas", "como trabajas",
    "qué modelo usas", "que modelo usas", "qué modelo de ia", "que modelo de ia",
    "modelo de ia usas", "modelo usas", "modelo utilizas", "qué ia usas",
    "que ia usas", "qué ia eres", "que ia eres", "modelo de lenguaje",
    # Preguntas dirigidas al producto (integración, seguridad, roadmap)
    "te integras", "integras con", "tienes integración", "tienes integracion",
    "qué integraciones", "que integraciones", "te conectas con", "eres seguro",
    "eres segura", "qué tan seguro eres", "que tan seguro eres", "mis datos están seguros",
    "mis datos estan seguros", "cómo proteges", "como proteges", "qué viene después",
    "que viene despues", "trabajo futuro", "qué falta por hacer", "que falta por hacer",
    "vas a tener", "vas a integrar",
]

# Interrogativos de significado/propósito (para combinar con una referencia meta).
_MEANING_TOKENS = [
    "qué es", "que es", "para qué", "para que", "objetivo", "propósito",
    "proposito", "alcance", "cómo funciona", "como funciona", "de qué trata",
    "de que trata", "qué hace", "que hace", "sirve", "modelo", "tecnología",
    "tecnologia", "resultado", "impacto", "quién creó", "quien creo", "quién hizo",
    "quien hizo", "creó", "creador", "autor", "desarrolló", "desarrollo", "hizo",
]


def mentions_platform(question: str) -> bool:
    """True si la pregunta MENCIONA la plataforma (por nombre o referencia), aunque
    no sea claramente una pregunta de significado. Se usa como red de seguridad: si
    el RAG no halló nada en los documentos y la pregunta alude a la plataforma, se
    responde con el conocimiento propio en vez de un "no encontré nada"."""
    q = (question or "").lower()
    if any(tok in q for tok in _NAME_TOKENS):
        return True
    if any(tok in q for tok in _SELF_TOKENS):
        return True
    for tok in _WEAK_SELF_TOKENS:
        if tok in q and f"{tok} de " not in q:
            return True
    return False


def is_platform_question(question: str) -> bool:
    """True si la pregunta es sobre SmartOnboard AI en sí (no sobre la empresa)."""
    q = (question or "").lower()
    if any(tok in q for tok in _NAME_TOKENS):
        return True
    if any(phrase in q for phrase in _IDENTITY_PHRASES):
        return True
    # Referencia demostrativa explícita a ESTA app: siempre es sobre la plataforma.
    if any(tok in q for tok in _SELF_TOKENS):
        return True
    # Referencia con artículo definido ("la plataforma") + interrogativo de
    # significado, pero solo si no viene calificada con "de …" (que indicaría un
    # sistema concreto de la empresa, p. ej. "la plataforma de nómina").
    if any(m in q for m in _MEANING_TOKENS):
        for tok in _WEAK_SELF_TOKENS:
            if tok in q and f"{tok} de " not in q:
                return True
    return False


# ─── SELECCIÓN DE ASPECTO (para el camino sin LLM) ───────────────────────────

# Prioridad: los aspectos más específicos primero, para que ganen sobre los
# genéricos cuando ambos podrían coincidir.
_ASPECT_ORDER = [
    "autor", "capacidades", "resultados", "estado", "roadmap", "integraciones",
    "seguridad", "modelo", "tecnologia", "funcionamiento", "alcance", "objetivo",
    "roles", "identidad",
]

_ASPECT_KEYWORDS = {
    "autor": ["quién creó", "quien creo", "quién hizo", "quien hizo", "quién desarrolló",
              "quien desarrollo", "autor", "creador", "de quién es", "de quien es",
              "quién lo hizo", "quien lo hizo", "quién está detrás", "quien esta detras",
              "lo creó", "lo creo", "la creó", "la creo", "quién lo desarrolló",
              "quien lo desarrollo", "quién los hizo", "quien los hizo"],
    "capacidades": ["en qué me ayud", "en que me ayud", "qué puedes hacer", "que puedes hacer",
                    "qué haces", "que haces", "para qué sirves", "para que sirves",
                    "cómo me ayudas", "como me ayudas", "en qué me puedes", "en que me puedes",
                    "qué sabes hacer", "que sabes hacer", "qué me ofreces", "que me ofreces"],
    "resultados": ["resultado", "impacto", "cuánto reduce", "cuanto reduce", "qué logra",
                   "que logra", "beneficios reales", "eficiencia", "cuántos días", "cuantos dias",
                   "tasa de resolución", "tasa de resolucion"],
    "estado": ["estado del proyecto", "en qué fase", "en que fase", "qué fase", "que fase",
               "en qué va", "en que va", "avance", "está terminado", "esta terminado",
               "está completo", "esta completo", "progreso del proyecto", "qué falta"],
    "roadmap": ["roadmap", "trabajo futuro", "a futuro", "proximamente", "próximamente",
                "que viene", "qué viene", "tendra", "tendrá", "habra", "habrá",
                "van a agregar", "piensan agregar", "proximas funciones", "próximas funciones",
                "mejoras futuras", "planeado", "que sigue", "qué sigue"],
    "integraciones": ["integra", "integración", "integracion", "integraciones", "jira",
                      "calendar", "google calendar", "correo", "email", "notificacion",
                      "notificación", "notificaciones", "sendgrid", "se conecta", "conecta con",
                      "te conectas", "sincroniza"],
    "seguridad": ["seguro", "segura", "seguridad", "gdpr", "datos personales", "privacidad",
                  "protección de datos", "proteccion de datos", "ley 1581", "1581",
                  "confidencial", "mis datos", "cifrado", "proteges", "protege mis"],
    "modelo": ["modelo", "qué ia", "que ia", "inteligencia artificial", "gpt", "openai", "llm",
               "fine-tuning", "fine tuning", "ajuste fino", "lora", "embedding", "ragas",
               "langgraph", "red neuronal"],
    "tecnologia": ["tecnología", "tecnologia", "arquitectura", "backend", "frontend",
                   "base de datos", "postgres", "docker", "fastapi", "next.js", "nextjs",
                   "stack", "lenguaje de programación", "lenguaje de programacion", "framework"],
    "funcionamiento": ["cómo funciona", "como funciona", "cómo trabaja", "como trabaja",
                       "cómo responde", "como responde", "rag", "cómo sabe", "como sabe",
                       "cómo lo hace", "como lo hace", "de dónde saca", "de donde saca",
                       "cómo busca", "como busca"],
    "alcance": ["alcance", "qué abarca", "que abarca", "qué incluye", "que incluye", "qué cubre",
                "que cubre", "funcionalidades", "qué ofrece", "que ofrece", "hasta dónde",
                "hasta donde", "permisos", "rbac", "control de acceso", "qué se puede hacer",
                "que se puede hacer"],
    "objetivo": ["objetivo", "propósito", "proposito", "para qué sirve", "para que sirve",
                 "beneficio", "qué problema", "que problema", "por qué existe", "por que existe",
                 "para qué se", "para que se", "meta", "para qué crearon", "para que crearon"],
    "roles": ["quién lo usa", "quien lo usa", "para quién", "para quien", "roles",
              "quién puede usar", "quien puede usar", "quién administra", "quien administra",
              "quién lo administra", "quien lo administra"],
    "identidad": ["qué es", "que es", "quién eres", "quien eres", "qué eres", "que eres",
                  "de qué trata", "de que trata", "cómo te llamas", "como te llamas",
                  "qué significa", "que significa", "smartonboard", "de qué va", "de que va"],
}


def _select_aspects(question: str) -> List[str]:
    q = (question or "").lower()
    return [a for a in _ASPECT_ORDER if any(kw in q for kw in _ASPECT_KEYWORDS[a])]


# Aspectos INTRÍNSECOS del producto (poco probables como consulta de la empresa).
# Se usan como red de seguridad: si el RAG no halló documentos y la pregunta toca
# uno de estos temas, se responde desde el conocimiento propio. Se dejan fuera los
# ambiguos (objetivo, alcance, resultados, tecnología, funcionamiento, roles,
# identidad) para no secuestrar preguntas legítimas de la empresa.
_FALLBACK_ASPECTS = {"integraciones", "seguridad", "roadmap", "autor", "estado", "capacidades"}


def is_product_topic(question: str) -> bool:
    """True si la pregunta toca un tema intrínseco del producto (integración,
    seguridad, roadmap, autor, estado, capacidades). Red de seguridad sobre RAG."""
    return any(a in _FALLBACK_ASPECTS for a in _select_aspects(question))


# Cierres variados para que la respuesta no suene repetitiva en demo.
_CLOSINGS = [
    "¿Quieres que profundice en algo más (objetivo, alcance, cómo funciona o el modelo de IA)?",
    "Si quieres, te cuento más sobre su alcance, cómo funciona o el modelo de IA que uso.",
    "¿Te sirve, o prefieres que entre en algún detalle (funcionamiento, seguridad, resultados)?",
    "Pregúntame lo que quieras: objetivo, alcance, integraciones, seguridad o cómo funciona por dentro.",
]


def _offline_answer(question: str, agent_name: str) -> str:
    """Responde SIN LLM enrutando al aspecto pedido. Devuelve el párrafo curado
    completo del aspecto (o el resumen de identidad si no reconoce el aspecto)."""
    name = (agent_name or "Sara").strip() or "Sara"
    hits = _select_aspects(question)
    if not hits:
        parts = [ASPECTS["identidad"], ASPECTS["capacidades"]]
    else:
        # Uno o dos aspectos como máximo: puntual, sin convertirse en un muro de texto.
        parts = [ASPECTS[a] for a in hits[:2]]
    body = "\n\n".join(parts)
    return f"{body}\n\nSoy {name}, tu asistente dentro de la plataforma. {random.choice(_CLOSINGS)}"


# ─── RESPUESTA CON LLM ───────────────────────────────────────────────────────

def _system_prompt(agent_name: str) -> str:
    return (
        f"Eres {agent_name}, la asistente de la plataforma SmartOnboard AI. "
        "El empleado pregunta por la PLATAFORMA en sí (qué es, para qué sirve, su "
        "alcance, cómo funciona, qué modelo de IA usa, sus objetivos o resultados). "
        "Responde en español, cálida y clara, usando EXCLUSIVAMENTE la información "
        "entre <kb></kb>; no inventes datos que no estén ahí. Sé puntual: responde en "
        "concreto a lo que preguntan, sin recitar todo. Si preguntan algo del producto "
        "que no está en la base, dilo con honestidad."
    )


def answer_platform_question(
    question: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.4,
    agent_name: str = "Sara",
    history: Optional[List[dict]] = None,
) -> str:
    """Responde una pregunta sobre la plataforma a partir del conocimiento propio.

    Con clave de IA redacta el LLM a partir de la base; sin clave responde nuestro
    modelo enrutando al aspecto (puntual y sin recortes)."""
    name = (agent_name or "Sara").strip() or "Sara"
    if not api_key:
        return _offline_answer(question, name)
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        llm = ChatOpenAI(model=model, temperature=temperature, openai_api_key=api_key, max_tokens=600)
        messages = [SystemMessage(content=_system_prompt(name))]
        for h in (history or [])[-4:]:
            if h.get("role") == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h.get("role") == "assistant":
                messages.append(AIMessage(content=h["content"]))
        messages.append(HumanMessage(content=f"<kb>\n{FULL_CONTEXT}\n</kb>\n\nPregunta: {question}"))
        return llm.invoke(messages).content.strip()
    except Exception:
        # Cualquier fallo del LLM cae a nuestro modelo offline por aspecto.
        return _offline_answer(question, name)
