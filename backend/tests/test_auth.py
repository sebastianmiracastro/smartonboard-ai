from tests.conftest import get_token


def test_login_exitoso(client, seed_data):
    resp = client.post("/api/auth/login", json={"email": "andrea@test.co", "password": "test123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_contrasena_incorrecta(client, seed_data):
    resp = client.post("/api/auth/login", json={"email": "andrea@test.co", "password": "incorrecta"})
    assert resp.status_code == 401


def test_login_email_inexistente(client, seed_data):
    resp = client.post("/api/auth/login", json={"email": "noexiste@test.co", "password": "test123"})
    assert resp.status_code == 401


def test_get_me_empleado(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "carlos@test.co"
    assert data["full_name"] == "Carlos Test"
    assert data["system_role"] == "empleado"


def test_get_me_rrhh(client, seed_data):
    token = get_token(client, "andrea@test.co", "test123")
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["system_role"] == "rrhh"


def test_get_me_sin_token(client, seed_data):
    resp = client.get("/api/users/me")
    assert resp.status_code in (401, 403)


def test_get_me_token_invalido(client, seed_data):
    resp = client.get("/api/users/me", headers={"Authorization": "Bearer token.falso.invalido"})
    assert resp.status_code in (401, 403)


def test_get_me_incluye_nombres_de_dept_y_rol(client, seed_data):
    token = get_token(client, "carlos@test.co", "test123")
    resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    data = resp.json()
    assert data.get("department_name") == "Ingeniería"
    assert data.get("role_name") == "Dev Junior"
