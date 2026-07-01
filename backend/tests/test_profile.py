"""Tests de la herramienta de perfil (consultar_mi_perfil) y del trato social,
a través del endpoint de chat en modo sin OPENAI_API_KEY (router heurístico).

Cubren que las preguntas sobre los datos del propio usuario en la plataforma
(plan, comprensión, documentos accesibles, cargo) se responden desde la BD y NO
caen a la búsqueda en documentos.
"""
import json

from app.models.models import (
    OnboardingPlan, EmployeePlan, EmployeeTask, Document, Conversation, ChatMessage,
)
from tests.conftest import get_token


def _conv(client, token):
    resp = client.post("/api/chat/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _send(client, token, conv_id, content):
    resp = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": content},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _assign_plan(db, done=1, total=2):
    plan = OnboardingPlan(id="plan-x", company_id="comp-test", name="Plan de Ventas")
    db.add(plan)
    db.flush()
    ep = EmployeePlan(company_id="comp-test", user_id="user-emp", plan_id="plan-x",
                      plan_name="Plan de Ventas", status="en_progreso")
    db.add(ep)
    db.flush()
    for i in range(total):
        db.add(EmployeeTask(
            user_id="user-emp", employee_plan_id=ep.id, title=f"Paso {i + 1}",
            category="lectura", status="completada" if i < done else "pendiente",
        ))
    db.commit()


# ─── PLAN ────────────────────────────────────────────────────────────────────

def test_pregunta_plan_usa_perfil_tool(client, seed_data, db_session):
    _assign_plan(db_session, done=1, total=2)
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿ahora mismo tengo un plan?")

    assert "consultar_mi_perfil" in json.loads(msg["tools_used"])
    assert "consultar_mis_tareas" not in json.loads(msg["tools_used"])
    assert "Plan de Ventas" in msg["content"]
    assert "50%" in msg["content"]  # 1 de 2 pasos


def test_sin_plan_responde_que_no(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿tengo un plan asignado?")

    assert "consultar_mi_perfil" in json.loads(msg["tools_used"])
    assert "no tienes ningún plan" in msg["content"].lower()


# ─── DOCUMENTOS ──────────────────────────────────────────────────────────────

def test_documentos_distingue_general_y_exclusivo(client, seed_data, db_session):
    db_session.add(Document(company_id="comp-test", name="Manual general",
                            status="indexado"))
    db_session.add(Document(company_id="comp-test", name="Guía de Ingeniería",
                            status="indexado", dept_permission="dept-eng"))
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿qué documentos tengo disponibles?")

    assert "consultar_mi_perfil" in json.loads(msg["tools_used"])
    contenido = msg["content"]
    assert "Manual general" in contenido and "Guía de Ingeniería" in contenido
    assert "exclusivo" in contenido and "general" in contenido


def test_documento_exclusivo_pregunta_directa(client, seed_data, db_session):
    db_session.add(Document(company_id="comp-test", name="Política de Ingeniería",
                            status="indexado", dept_permission="dept-eng"))
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿tengo algún documento exclusivo?")

    assert "Política de Ingeniería" in msg["content"]
    assert "exclusivo" in msg["content"].lower()


# ─── COMPRENSIÓN ─────────────────────────────────────────────────────────────

def test_comprension_reporta_porcentaje(client, seed_data, db_session):
    conv = Conversation(user_id="user-emp", title="previa")
    db_session.add(conv)
    db_session.flush()
    db_session.add(ChatMessage(conversation_id=conv.id, role="assistant",
                               content="r", comprehension_score=0.8, category="procesos"))
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿cuál es mi porcentaje de entendimiento?")

    assert "consultar_mi_perfil" in json.loads(msg["tools_used"])
    assert "80%" in msg["content"]


# ─── PERFIL GENERAL ──────────────────────────────────────────────────────────

def test_cargo_y_area(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿cuál es mi cargo y mi área?")

    assert "consultar_mi_perfil" in json.loads(msg["tools_used"])
    assert "Dev Junior" in msg["content"]
    assert "Ingeniería" in msg["content"]


# ─── LA MÉTRICA NO SE CONTAMINA ──────────────────────────────────────────────

def test_perfil_no_guarda_comprension(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    conv_id = _conv(client, token)
    _send(client, token, conv_id, "¿cuál es mi cargo?")

    saved = db_session.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv_id, ChatMessage.role == "assistant"
    ).first()
    assert saved is not None
    assert saved.comprehension_score is None


# ─── TRATO SOCIAL ────────────────────────────────────────────────────────────

def test_saludo_es_social_y_no_busca(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    conv_id = _conv(client, token)
    msg = _send(client, token, conv_id, "hola")

    assert json.loads(msg["tools_used"]) == []
    # Todas las variantes de saludo ofrecen ayuda (ancla estable).
    assert "ayud" in msg["content"].lower()
    saved = db_session.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv_id, ChatMessage.role == "assistant"
    ).first()
    assert saved.comprehension_score is None


def test_gracias_es_social(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "muchas gracias")
    assert json.loads(msg["tools_used"]) == []
    assert "gusto" in msg["content"].lower() or "aquí estoy" in msg["content"].lower()


# ─── PLATAFORMA POR EL ENDPOINT ──────────────────────────────────────────────

def test_pregunta_de_plataforma_responde_desde_kb(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿qué es SmartOnboard AI?")

    assert json.loads(msg["tools_used"]) == []
    assert "SmartOnboard AI" in msg["content"]
    assert "onboarding" in msg["content"].lower()


def test_offline_sin_documentos_avisa_que_no_hay(client, seed_data, db_session):
    # seed_data no tiene documentos → una pregunta informativa debe avisar que aún
    # no hay documentos cargados (no el genérico 'no encontré sobre eso').
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token),
                "¿cuál es la política de reembolsos de gastos de viaje?")
    assert "no hay documentos cargados" in msg["content"].lower()


def test_offline_mensajes_distinguen_estado():
    from app.services.agent import generate_mock_answer
    sin = generate_mock_answer("x", "", has_any_docs=False).lower()
    con = generate_mock_answer("x", "", has_any_docs=True).lower()
    assert "no hay documentos cargados" in sin
    assert "no encontré información específica" in con


def test_pregunta_integracion_jira(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿SmartOnboard se integra con Jira?")
    assert json.loads(msg["tools_used"]) == []
    assert "Jira" in msg["content"]


def test_integracion_sin_referencia_usa_fallback(client, seed_data, db_session):
    # Sin documentos y sin decir "la plataforma": la red de seguridad responde
    # desde el conocimiento propio porque es un tema intrínseco del producto.
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿se integra con Jira?")
    assert "Jira" in msg["content"]


def test_seguridad_sin_referencia_usa_fallback(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿es seguro? ¿protege mis datos?")
    contenido = msg["content"].lower()
    assert "rbac" in contenido or "jwt" in contenido or "1581" in contenido


def test_followup_documento_general_usa_contexto(client, seed_data, db_session):
    db_session.add(Document(company_id="comp-test", name="Manual general",
                            status="indexado"))
    db_session.add(Document(company_id="comp-test", name="Política de Ingeniería",
                            status="indexado", dept_permission="dept-eng"))
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    conv_id = _conv(client, token)
    _send(client, token, conv_id, "¿tengo algún documento exclusivo?")
    # Follow-up corto sin sustantivo: debe retomar el tema (documentos) y aplicar
    # el nuevo calificador (general), no el anterior (exclusivo).
    msg = _send(client, token, conv_id, "¿y uno general?")

    assert "consultar_mi_perfil" in json.loads(msg["tools_used"])
    assert "Manual general" in msg["content"]
    assert "general" in msg["content"].lower()


def test_comprension_desglose_por_categoria(client, seed_data, db_session):
    conv = Conversation(user_id="user-emp", title="previa")
    db_session.add(conv)
    db_session.flush()
    db_session.add(ChatMessage(conversation_id=conv.id, role="assistant",
                               content="r1", comprehension_score=0.9, category="procesos"))
    db_session.add(ChatMessage(conversation_id=conv.id, role="assistant",
                               content="r2", comprehension_score=0.4, category="cultura"))
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    msg = _send(client, token, _conv(client, token), "¿cómo voy en mi comprensión por tema?")

    assert "consultar_mi_perfil" in json.loads(msg["tools_used"])
    assert "Por tema" in msg["content"]
    assert "procesos" in msg["content"] and "cultura" in msg["content"]
