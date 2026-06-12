from sqlalchemy.orm import Session
from app.models.models import Company, User
from app.core.security import hash_password
from tests.conftest import get_token


def test_listar_usuarios_como_rrhh(client, seed_data):
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/users/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "carlos@test.co" in emails
    assert "andrea@test.co" in emails


def test_listar_usuarios_como_empleado_prohibido(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/users/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_obtener_usuario_misma_empresa(client, seed_data):
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/users/user-emp", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "carlos@test.co"


def test_obtener_usuario_otra_empresa_retorna_404(client, seed_data, db_session: Session):
    # Crear empresa y usuario externos
    otra = Company(id="comp-ext", name="Otra Corp", slug="otra-corp")
    db_session.add(otra)
    intruso = User(
        id="user-ext",
        company_id="comp-ext",
        full_name="Usuario Externo",
        email="externo@otra.co",
        hashed_password=hash_password("test123"),
        system_role="empleado",
        status="activo",
    )
    db_session.add(intruso)
    db_session.commit()

    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/users/user-ext", headers={"Authorization": f"Bearer {token}"})
    # El filtro company_id debe devolver 404 aunque el usuario exista en otra empresa
    assert resp.status_code == 404


def test_obtener_usuario_devuelve_department_name(client, seed_data):
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/users/user-emp", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert data["department_name"] == "Ingeniería"
    assert data["role_name"] == "Dev Junior"


def test_lista_no_incluye_usuarios_de_otra_empresa(client, seed_data, db_session: Session):
    otra = Company(id="comp-y", name="Y Corp", slug="y-corp")
    db_session.add(otra)
    foraneo = User(
        id="user-y",
        company_id="comp-y",
        full_name="Foráneo",
        email="foraneo@y.co",
        hashed_password=hash_password("test123"),
        system_role="empleado",
        status="activo",
    )
    db_session.add(foraneo)
    db_session.commit()

    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/users/", headers={"Authorization": f"Bearer {token}"})
    emails = [u["email"] for u in resp.json()]
    assert "foraneo@y.co" not in emails
