"""Tests del auto-conocimiento de la plataforma (services/platform_kb.py).

Son unitarios puros (sin BD ni LLM): validan la detección y las respuestas
offline por aspecto que da "nuestro modelo" cuando no hay clave de OpenAI.
"""
import pytest

from app.services.platform_kb import (
    is_platform_question,
    mentions_platform,
    answer_platform_question,
    _select_aspects,
)


@pytest.mark.parametrize("q", [
    "¿qué es SmartOnboard AI?",
    "para qué sirve esta plataforma",
    "cuál es el objetivo de la plataforma",
    "qué alcance tiene este sistema",
    "qué modelo de IA usas",
    "cómo funcionas",
    "quién eres",
    "en qué me puedes ayudar",
    "quién creó esta plataforma",
])
def test_detecta_preguntas_de_plataforma(q):
    assert is_platform_question(q) or mentions_platform(q)


@pytest.mark.parametrize("q", [
    "cómo pido vacaciones",
    "cuál es la política de trabajo remoto",
    "cómo accedo a la plataforma de nómina",
    "qué es el sistema de beneficios de la empresa",
    "cuál es el objetivo del área de ventas",
    "dónde encuentro el manual de bienvenida",
])
def test_no_confunde_preguntas_de_la_empresa(q):
    assert not is_platform_question(q)
    assert not mentions_platform(q)


def test_respuesta_objetivo_es_puntual():
    r = answer_platform_question("cuál es el objetivo de la plataforma", api_key=None)
    assert "objetivo" in r.lower()
    assert "reducir el tiempo de incorporación" in r.lower()


def test_respuesta_modelo_menciona_tecnologia_de_ia():
    r = answer_platform_question("qué modelo de IA usas", api_key=None).lower()
    assert "all-minilm" in r or "gpt-4o mini" in r or "lora" in r


def test_respuesta_identidad_menciona_el_producto():
    r = answer_platform_question("qué es SmartOnboard AI", api_key=None).lower()
    assert "smartonboard ai" in r
    assert "onboarding" in r


def test_seleccion_de_aspecto_es_correcta():
    assert _select_aspects("cuál es el objetivo")[0] == "objetivo"
    assert _select_aspects("qué alcance tiene")[0] == "alcance"
    assert _select_aspects("quién lo creó") == ["autor"]


@pytest.mark.parametrize("q,esperado", [
    ("¿se integra con Jira?", "integraciones"),
    ("¿qué integraciones tiene?", "integraciones"),
    ("¿es seguro? ¿protege mis datos?", "seguridad"),
    ("¿qué viene después? ¿trabajo futuro?", "roadmap"),
])
def test_nuevos_aspectos_se_seleccionan(q, esperado):
    assert esperado in _select_aspects(q)


def test_respuesta_integraciones_menciona_jira():
    r = answer_platform_question("qué integraciones tiene la plataforma", api_key=None)
    assert "Jira" in r


def test_respuesta_seguridad_menciona_rbac_o_ley():
    r = answer_platform_question("es seguro, cómo proteges mis datos", api_key=None).lower()
    assert "rbac" in r or "1581" in r or "jwt" in r


def test_detecta_integracion_y_roadmap_dirigidos_al_producto():
    assert is_platform_question("¿te integras con Jira?")
    assert is_platform_question("¿qué viene después?")


def test_respuesta_offline_no_queda_cortada():
    # La respuesta se arma con párrafos completos: debe terminar en signo de cierre.
    r = answer_platform_question("cómo funciona la plataforma", api_key=None).strip()
    assert r.endswith((".", "?", "!")) and "…" not in r.split("\n")[0]
