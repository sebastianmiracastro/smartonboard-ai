from app.models.models import EmployeeTask
from tests.conftest import get_token


def test_mis_tareas_vacio(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/tasks/my", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_mis_tareas_devuelve_solo_las_propias(client, seed_data, db_session):
    t1 = EmployeeTask(id="t1", user_id="user-emp", title="Tarea mía", status="pendiente")
    t2 = EmployeeTask(id="t2", user_id="user-rrhh", title="Tarea ajena", status="pendiente")
    db_session.add_all([t1, t2])
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/tasks/my", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert "t1" in ids
    assert "t2" not in ids


def test_completar_tarea_propia(client, seed_data, db_session):
    tarea = EmployeeTask(id="t3", user_id="user-emp", title="Completable", status="pendiente")
    db_session.add(tarea)
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    resp = client.patch("/api/tasks/t3/complete", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    db_session.refresh(tarea)
    assert tarea.status == "completada"


def test_completar_tarea_ajena_retorna_404(client, seed_data, db_session):
    tarea = EmployeeTask(id="t4", user_id="user-rrhh", title="Ajena", status="pendiente")
    db_session.add(tarea)
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    resp = client.patch("/api/tasks/t4/complete", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_actualizar_status_invalido_retorna_400(client, seed_data, db_session):
    tarea = EmployeeTask(id="t5", user_id="user-emp", title="Status test", status="pendiente")
    db_session.add(tarea)
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    resp = client.patch(
        "/api/tasks/t5/status",
        params={"status": "INVALIDO"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "Estado inválido" in resp.json()["detail"]


def test_actualizar_status_valido(client, seed_data, db_session):
    tarea = EmployeeTask(id="t6", user_id="user-emp", title="En progreso", status="pendiente")
    db_session.add(tarea)
    db_session.commit()

    token = get_token(client, "carlos@test.co", "test123")
    resp = client.patch(
        "/api/tasks/t6/status",
        params={"status": "en_progreso"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    db_session.refresh(tarea)
    assert tarea.status == "en_progreso"


def test_rrhh_obtiene_tareas_de_empleado(client, seed_data, db_session):
    t = EmployeeTask(id="t7", user_id="user-emp", title="Tarea visible para RR.HH.", status="pendiente")
    db_session.add(t)
    db_session.commit()

    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/tasks/user/user-emp", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert "t7" in ids


def test_rrhh_no_obtiene_tareas_de_empleado_otra_empresa(client, seed_data, db_session):
    from app.models.models import Company, User
    from app.core.security import hash_password
    otra = Company(id="comp-z", name="Z Corp", slug="z-corp")
    db_session.add(otra)
    emp_z = User(
        id="user-z", company_id="comp-z",
        full_name="Foráneo Z", email="z@z.co",
        hashed_password=hash_password("test123"),
        system_role="empleado", status="activo",
    )
    db_session.add(emp_z)
    db_session.commit()

    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/tasks/user/user-z", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_empleado_no_puede_ver_tareas_de_otro(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/tasks/user/user-rrhh", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
