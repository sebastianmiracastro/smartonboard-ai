"""Tests del progreso de onboarding derivado de los planes (no de días fijos)."""
import json

from app.models.models import User, OnboardingPlan, EmployeePlan, EmployeeTask
from app.services.onboarding import compute_onboarding_progress
from tests.conftest import get_token


def _plan(db, pid, name="Plan"):
    p = OnboardingPlan(id=pid, company_id="comp-test", name=name)
    db.add(p)
    db.flush()
    return p


def _ep(db, pid, status, pasos):
    """Crea un EmployeePlan para user-emp con `pasos` = lista de estados de tarea."""
    ep = EmployeePlan(company_id="comp-test", user_id="user-emp", plan_id=pid,
                      plan_name="Plan", status=status)
    db.add(ep)
    db.flush()
    for i, st in enumerate(pasos):
        db.add(EmployeeTask(user_id="user-emp", employee_plan_id=ep.id,
                            title=f"paso {i}", category="lectura", status=st))
    db.flush()
    return ep


def _user(db):
    return db.query(User).filter(User.id == "user-emp").first()


def test_sin_plan(seed_data, db_session):
    p = compute_onboarding_progress(db_session, _user(db_session))
    assert p["state"] == "sin_plan" and p["percent"] == 0


def test_en_curso_calcula_porcentaje(seed_data, db_session):
    _plan(db_session, "plan-a")
    _ep(db_session, "plan-a", "en_progreso", ["completada", "pendiente"])
    db_session.commit()

    p = compute_onboarding_progress(db_session, _user(db_session))
    assert p["state"] == "onboarding"
    assert p["percent"] == 50
    assert p["steps_done"] == 1 and p["steps_total"] == 2


def test_completado_y_reasignacion_reaparece(seed_data, db_session):
    # Un plan finalizado y ninguno en curso → completado (100%).
    _plan(db_session, "plan-b")
    _ep(db_session, "plan-b", "finalizado", ["completada", "completada"])
    db_session.commit()
    p1 = compute_onboarding_progress(db_session, _user(db_session))
    assert p1["state"] == "completado" and p1["percent"] == 100

    # Se asigna un plan nuevo → vuelve a 'onboarding' y la barra reaparece en 0%.
    _plan(db_session, "plan-c")
    _ep(db_session, "plan-c", "sin_empezar", ["pendiente", "pendiente"])
    db_session.commit()
    p2 = compute_onboarding_progress(db_session, _user(db_session))
    assert p2["state"] == "onboarding" and p2["percent"] == 0


def test_varios_planes_en_curso_se_agregan(seed_data, db_session):
    _plan(db_session, "plan-d")
    _plan(db_session, "plan-e")
    _ep(db_session, "plan-d", "en_progreso", ["completada", "completada", "pendiente"])
    _ep(db_session, "plan-e", "en_progreso", ["completada", "pendiente"])
    db_session.commit()
    p = compute_onboarding_progress(db_session, _user(db_session))
    # 3 de 5 pasos completados
    assert p["steps_done"] == 3 and p["steps_total"] == 5 and p["percent"] == 60


def test_api_me_expone_progreso(client, seed_data, db_session):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "onboarding_progress" in body and "onboarding_state" in body
    assert body["onboarding_state"] == "sin_plan"
