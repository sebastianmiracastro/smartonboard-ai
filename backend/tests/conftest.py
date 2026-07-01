import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.models.models import Company, Department, Role, User, OnboardingPlan, OnboardingTask, EmployeeTask, Document
from app.core.security import hash_password
from main import app

# Base de datos de PRUEBA en PostgreSQL. Por defecto usa el mismo contenedor
# `db` (mapeado a localhost:5432) pero una base independiente para no tocar
# los datos de desarrollo. Se puede sobreescribir con la variable de entorno.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://smartonboard:smartonboard123@localhost:5432/smartonboard_test",
)


def _ensure_test_database(url: str) -> None:
    """Crea la base de datos de prueba si aún no existe (idempotente)."""
    target = make_url(url)
    db_name = target.database
    # Conexión a la base de mantenimiento `postgres` para poder crear la de prueba.
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()


@pytest.fixture(scope="function")
def db_session():
    _ensure_test_database(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def seed_data(db_session):
    company = Company(id="comp-test", name="Test Corp", slug="test-corp", industry="Tech")
    db_session.add(company)

    dept_rrhh = Department(id="dept-rrhh", company_id="comp-test", name="RR.HH.", is_rrhh=True, color="#10b981")
    dept_eng = Department(id="dept-eng", company_id="comp-test", name="Ingeniería", is_rrhh=False, color="#6366f1")
    db_session.add_all([dept_rrhh, dept_eng])

    role_rrhh = Role(id="role-rrhh", department_id="dept-rrhh", name="Analista RR.HH.", seniority_level=2, seniority_label="Mid")
    role_dev = Role(id="role-dev", department_id="dept-eng", name="Dev Junior", seniority_level=1, seniority_label="Junior")
    db_session.add_all([role_rrhh, role_dev])

    user_rrhh = User(
        id="user-rrhh",
        company_id="comp-test",
        department_id="dept-rrhh",
        role_id="role-rrhh",
        full_name="Andrea Test",
        email="andrea@test.co",
        hashed_password=hash_password("test123"),
        system_role="rrhh",
        status="activo",
        onboarding_day=15,
        onboarding_total_days=15,
    )
    user_emp = User(
        id="user-emp",
        company_id="comp-test",
        department_id="dept-eng",
        role_id="role-dev",
        full_name="Carlos Test",
        email="carlos@test.co",
        hashed_password=hash_password("test123"),
        system_role="empleado",
        status="onboarding",
        onboarding_day=3,
        onboarding_total_days=15,
        start_date="2026-03-01",
    )
    db_session.add_all([user_rrhh, user_emp])
    db_session.commit()

    return {
        "company": company,
        "dept_rrhh": dept_rrhh,
        "dept_eng": dept_eng,
        "role_rrhh": role_rrhh,
        "role_dev": role_dev,
        "user_rrhh": user_rrhh,
        "user_emp": user_emp,
    }


def get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]
