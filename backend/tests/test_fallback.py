"""Tests del FALLBACK léxico (re-lectura de documentos) y de la INTERVENCIÓN HUMANA
(escalado a RR.HH. cuando no hay respuesta acorde a la pregunta)."""
import json

from app.models.models import Document, DocumentChunk, RRHHAlert, User
from app.services import agent as agent_mod
from app.services.agent import run_agent
from app.services.agent_tools import ToolContext
from app.services.embeddings import generate_embedding


def _ctx(db):
    return ToolContext(db=db, user_id="user-emp", company_id="comp-test",
                       user_is_rrhh=False, user_seniority_level=1,
                       user_department_id="dept-eng", user_role_id="role-dev")


def _run(db, question, api_key=None):
    u = db.query(User).filter(User.id == "user-emp").first()
    return run_agent(question=question, company_id="comp-test", db=db, user_id=u.id,
                     user_is_rrhh=False, user_seniority_level=1,
                     user_department_id=u.department_id, user_role_id=u.role_id,
                     openai_api_key=api_key)


# ─── FALLBACK LÉXICO ─────────────────────────────────────────────────────────

def test_fallback_encuentra_por_palabra_clave(seed_data, db_session):
    db_session.add(Document(id="doc-x", company_id="comp-test", name="Reglamento",
                            status="indexado", uploaded_by="user-rrhh"))
    db_session.add(DocumentChunk(
        document_id="doc-x", company_id="comp-test", chunk_index=0, category="cultura",
        content="El código de vestimenta es formal de lunes a jueves y casual los viernes.",
    ))
    db_session.commit()

    ctx = _ctx(db_session)
    out = ctx.reconsultar_documentos("¿cuál es el código de vestimenta?")
    assert "vestimenta" in out
    assert ctx.sources and ctx.retrieved_chunks


def test_fallback_sin_coincidencia_devuelve_vacio(seed_data, db_session):
    db_session.add(Document(id="doc-y", company_id="comp-test", name="Menú",
                            status="indexado", uploaded_by="user-rrhh"))
    db_session.add(DocumentChunk(
        document_id="doc-y", company_id="comp-test", chunk_index=0,
        content="El menú de la cafetería cambia cada semana en la sede norte.",
    ))
    db_session.commit()

    ctx = _ctx(db_session)
    assert ctx.reconsultar_documentos("configuración de servidores kubernetes") == ""


# ─── INTERVENCIÓN HUMANA ─────────────────────────────────────────────────────

def test_intervencion_humana_sin_clave_cuando_no_hay_respuesta(seed_data, db_session):
    # Documento existente pero AJENO a la pregunta (y sin embedding → el índice
    # semántico lo salta; el fallback léxico tampoco encuentra las palabras).
    db_session.add(Document(id="doc-u", company_id="comp-test", name="Menú",
                            status="indexado", uploaded_by="user-rrhh"))
    db_session.add(DocumentChunk(
        document_id="doc-u", company_id="comp-test", chunk_index=0, embedding=None,
        content="El menú de la cafetería cambia cada semana en la sede norte.",
    ))
    db_session.commit()

    r = _run(db_session, "¿cómo configuro el acceso VPN corporativo?", api_key=None)
    assert "RR.HH" in r["answer"]
    assert "escalar_a_rrhh" in r["tools_used"]
    assert r["comprehension_score"] is None
    alerta = db_session.query(RRHHAlert).filter_by(user_id="user-emp").first()
    assert alerta is not None and alerta.kind == "sin_respuesta"


def test_intervencion_humana_con_clave_si_llm_no_responde(seed_data, db_session, monkeypatch):
    content = "El horario de oficina es de 8am a 5pm de lunes a viernes."
    db_session.add(Document(id="doc-h", company_id="comp-test", name="Horarios",
                            status="indexado", uploaded_by="user-rrhh"))
    db_session.add(DocumentChunk(
        document_id="doc-h", company_id="comp-test", chunk_index=0, category="procesos",
        content=content, embedding=json.dumps(generate_embedding(content)),
    ))
    db_session.commit()

    class _FakeNo:
        def __init__(self, *a, **k):
            pass

        def invoke(self, messages):
            class _R:
                content = "NO_TENGO_RESPUESTA"
            return _R()

    monkeypatch.setattr(agent_mod, "ChatOpenAI", _FakeNo)

    r = _run(db_session, "¿cuál es el horario de oficina?", api_key="sk-test")
    assert "RR.HH" in r["answer"]                    # mensaje de intervención humana
    assert "escalar_a_rrhh" in r["tools_used"]        # se creó la alerta
    assert r["comprehension_score"] is None           # sin respuesta → no cuenta
    alerta = db_session.query(RRHHAlert).filter_by(user_id="user-emp").first()
    assert alerta is not None and alerta.kind == "sin_respuesta"
