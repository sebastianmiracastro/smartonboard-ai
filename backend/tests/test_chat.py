"""Tests del agente con herramientas en el endpoint de chat (modo sin OPENAI_API_KEY,
es decir router heurístico que invoca las herramientas reales sobre la BD)."""
import json

from app.models.models import EmployeeTask, RRHHAlert, ChatMessage
from tests.conftest import get_token


def _new_conversation(client, token):
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


def test_consultar_mis_tareas_usa_tool(client, seed_data, db_session):
    db_session.add(EmployeeTask(user_id="user-emp", title="Configurar entorno",
                                category="configuracion", day_number=2, status="pendiente"))
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    conv_id = _new_conversation(client, token)
    msg = _send(client, token, conv_id, "¿Cuáles son mis tareas?")

    tools = json.loads(msg["tools_used"])
    assert "consultar_mis_tareas" in tools
    assert "Configurar entorno" in msg["content"]


def test_completar_tarea_actualiza_estado(client, seed_data, db_session):
    db_session.add(EmployeeTask(user_id="user-emp", title="Configurar entorno de desarrollo",
                                category="configuracion", day_number=2, status="pendiente"))
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    conv_id = _new_conversation(client, token)
    msg = _send(client, token, conv_id, "Ya terminé la tarea de configurar el entorno, márcala como completada")

    assert "completar_tarea" in json.loads(msg["tools_used"])
    tarea = db_session.query(EmployeeTask).filter(EmployeeTask.user_id == "user-emp").first()
    assert tarea.status == "completada"
    assert tarea.completed_at is not None


def test_escalar_a_rrhh_crea_alerta(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    conv_id = _new_conversation(client, token)
    msg = _send(client, token, conv_id, "Estoy muy perdido, necesito ayuda de alguien")

    assert "escalar_a_rrhh" in json.loads(msg["tools_used"])
    alertas = db_session.query(RRHHAlert).filter(RRHHAlert.user_id == "user-emp").all()
    assert len(alertas) == 1
    assert alertas[0].status == "pendiente"


def test_pregunta_informativa_no_inventa_tool_de_tareas(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    conv_id = _new_conversation(client, token)
    msg = _send(client, token, conv_id, "¿Cómo solicito vacaciones?")

    tools = json.loads(msg["tools_used"])
    assert "consultar_mis_tareas" not in tools
    assert "completar_tarea" not in tools
    # Persistencia correcta del mensaje del asistente
    saved = db_session.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv_id, ChatMessage.role == "assistant"
    ).first()
    assert saved is not None and saved.tools_used is not None
