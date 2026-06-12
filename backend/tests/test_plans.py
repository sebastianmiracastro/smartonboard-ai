from app.models.models import Company, OnboardingPlan, OnboardingTask
from tests.conftest import get_token


def _crear_plan(db_session, plan_id: str, company_id: str, num_tasks: int = 2):
    plan = OnboardingPlan(
        id=plan_id, company_id=company_id,
        name=f"Plan {plan_id}", duration_days=15
    )
    db_session.add(plan)
    for i in range(num_tasks):
        db_session.add(OnboardingTask(
            id=f"{plan_id}-t{i}",
            plan_id=plan_id,
            title=f"Tarea {i}",
            day_number=i + 1,
        ))
    db_session.commit()
    return plan


def test_listar_planes_como_rrhh(client, seed_data, db_session):
    _crear_plan(db_session, "plan-a", "comp-test")
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/plans/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert "plan-a" in ids


def test_listar_planes_como_empleado_prohibido(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/plans/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_obtener_tareas_plan_misma_empresa(client, seed_data, db_session):
    _crear_plan(db_session, "plan-b", "comp-test", num_tasks=3)
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/plans/plan-b/tasks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_obtener_tareas_plan_otra_empresa_retorna_404(client, seed_data, db_session):
    # Plan de otra empresa
    otra = Company(id="comp-ajena", name="Ajena Corp", slug="ajena-corp")
    db_session.add(otra)
    db_session.commit()
    _crear_plan(db_session, "plan-ajena", "comp-ajena", num_tasks=1)

    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/plans/plan-ajena/tasks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_obtener_tareas_plan_inexistente_retorna_404(client, seed_data):
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/plans/plan-fantasma/tasks", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_crear_plan_como_rrhh(client, seed_data):
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.post(
        "/api/plans/",
        json={"name": "Nuevo Plan", "duration_days": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Nuevo Plan"
    assert data["company_id"] == "comp-test"


def test_crear_plan_como_empleado_prohibido(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.post(
        "/api/plans/",
        json={"name": "Plan ilegal", "duration_days": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
