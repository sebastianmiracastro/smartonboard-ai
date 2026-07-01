"""Verifica a fondo las dos rutas del agente:

- CON clave de IA de la empresa: la clave interviene para redactar/mejorar la
  respuesta (informativa, plataforma, perfil en prosa). Se mockea el LLM para no
  gastar tokens ni necesitar una clave real.
- SIN clave: las preguntas de PERFIL y de DOCUMENTOS se responden igual (BD +
  sintetizador extractivo propio).
"""
import json

import pytest

from app.models.models import Document, DocumentChunk, User
from app.services import agent as agent_mod
from app.services.agent import run_agent, _answer_grounded, refine_answer
from app.services.embeddings import generate_embedding


LLM_MARK = "RESPUESTA_REDACTADA_POR_LLM"


class _FakeLLM:
    """Sustituto de ChatOpenAI: no llama a la red, devuelve un texto fijo."""
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, messages):
        class _R:
            content = LLM_MARK
        return _R()


@pytest.fixture
def fake_llm(monkeypatch):
    # Camino del agente (import a nivel de módulo).
    monkeypatch.setattr(agent_mod, "ChatOpenAI", _FakeLLM)
    # Camino de plataforma (import perezoso dentro de la función).
    monkeypatch.setattr("langchain_openai.ChatOpenAI", _FakeLLM, raising=False)
    return _FakeLLM


def _add_doc_chunk(db, content, doc_id="doc-vac"):
    db.add(Document(id=doc_id, company_id="comp-test", name="Vacaciones", format="txt",
                    status="indexado", uploaded_by="user-rrhh"))
    db.add(DocumentChunk(document_id=doc_id, company_id="comp-test", content=content,
                         chunk_index=0, embedding=json.dumps(generate_embedding(content)),
                         category="procesos"))
    db.commit()


def _run(db, question, api_key=None):
    u = db.query(User).filter(User.id == "user-emp").first()
    return run_agent(
        question=question, company_id="comp-test", db=db, user_id=u.id,
        user_is_rrhh=False, user_seniority_level=1,
        user_department_id=u.department_id, user_role_id=u.role_id,
        openai_api_key=api_key,
    )


# ─── UNIDAD: la clave interviene ─────────────────────────────────────────────

def test_answer_grounded_usa_el_llm(fake_llm):
    out = _answer_grounded("¿cómo pido vacaciones?", "contexto de prueba", [],
                           api_key="sk-test")
    assert out == LLM_MARK


def test_refine_conserva_borrador_sin_clave():
    draft = "Eres Carlos, cargo Dev Junior. Estado: en onboarding."
    assert refine_answer("¿mi cargo?", draft, api_key=None) == draft


def test_refine_con_clave_usa_llm(fake_llm):
    out = refine_answer("¿mi cargo?", "Eres Carlos, cargo Dev Junior.", api_key="sk-test")
    assert out == LLM_MARK


# ─── CON CLAVE (end-to-end, LLM mockeado) ────────────────────────────────────

def test_informativa_con_clave_redacta_con_llm(seed_data, db_session, fake_llm):
    _add_doc_chunk(db_session, "Para solicitar tus vacaciones escribe a Recursos "
                               "Humanos con dos semanas de anticipación.")
    r = _run(db_session, "¿cómo solicito mis vacaciones?", api_key="sk-test")
    assert r["answer"] == LLM_MARK                      # lo redactó el LLM
    assert "buscar_en_documentos" in r["tools_used"]    # sobre documentos reales
    assert r["sources"]                                 # citando fuentes


def test_perfil_prosa_con_clave_se_refina(seed_data, db_session, fake_llm):
    r = _run(db_session, "¿cuál es mi cargo y mi área?", api_key="sk-test")
    assert r["answer"] == LLM_MARK                      # el LLM pulió la redacción


def test_perfil_documentos_con_clave_no_se_refina(seed_data, db_session, fake_llm):
    db_session.add(Document(id="d1", company_id="comp-test", name="Manual general",
                            status="indexado", uploaded_by="user-rrhh"))
    db_session.commit()
    r = _run(db_session, "¿qué documentos tengo disponibles?", api_key="sk-test")
    # La lista NO se pasa por el LLM (se dañaría): sigue siendo la respuesta de la BD.
    assert r["answer"] != LLM_MARK
    assert "Manual general" in r["answer"]


def test_plataforma_con_clave_usa_llm(seed_data, db_session, fake_llm):
    r = _run(db_session, "¿qué es SmartOnboard AI?", api_key="sk-test")
    assert r["answer"] == LLM_MARK


# ─── SIN CLAVE (perfil y documentos igual se responden) ──────────────────────

def test_perfil_sin_clave_responde_desde_bd(seed_data, db_session):
    r = _run(db_session, "¿cuál es mi cargo y mi área?", api_key=None)
    assert "consultar_mi_perfil" in r["tools_used"]
    assert "Dev Junior" in r["answer"] and "Ingeniería" in r["answer"]


def test_documentos_sin_clave_responde_extractivo(seed_data, db_session):
    _add_doc_chunk(db_session, "Para solicitar tus vacaciones escribe a Recursos "
                               "Humanos con dos semanas de anticipación.")
    r = _run(db_session, "¿cómo solicito mis vacaciones?", api_key=None)
    assert "buscar_en_documentos" in r["tools_used"]
    # El sintetizador extractivo devuelve el contenido real del documento.
    assert "Recursos Humanos" in r["answer"] or "dos semanas" in r["answer"]
