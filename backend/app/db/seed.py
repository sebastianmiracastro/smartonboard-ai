"""Seed MÍNIMO: una empresa, 2 departamentos (RR.HH. y TI) y 2 usuarios
(uno con acceso RR.HH. y uno normal). SIN documentos, tareas, planes ni nómina:
la app arranca casi limpia para manejar la data desde 0.

Uso (sobre una BD vacía):
    cd backend
    venv\\Scripts\\activate
    python -m app.db.seed
"""
from app.db.database import SessionLocal, engine
from app.models import models
from app.db.migrate import run_migrations
from app.models.models import Company, Department, Role, User
from app.core.security import hash_password


def seed():
    # Crear tablas y aplicar migraciones (para que el seed funcione standalone)
    models.Base.metadata.create_all(bind=engine)
    run_migrations()

    db = SessionLocal()
    try:
        if db.query(Company).first():
            print("La base de datos ya tiene datos, se omite el seed.")
            return

        print("Creando datos mínimos...")

        # Empresa
        company = Company(id="comp-001", name="TechCorp S.A.S.", slug="techcorp", industry="Tecnología")
        db.add(company)
        db.flush()

        # Departamentos: TI y RR.HH.
        dept_ti = Department(id="dept-ti", company_id="comp-001", name="Tecnología",
                             description="Desarrollo y sistemas", is_rrhh=False, is_gerencia=False, color="#6d5cff")
        dept_rrhh = Department(id="dept-rrhh", company_id="comp-001", name="Recursos Humanos",
                               description="Gestión del talento", is_rrhh=True, is_gerencia=False, color="#10b981")
        db.add_all([dept_ti, dept_rrhh])
        db.flush()

        # Un cargo por departamento
        role_dev = Role(id="role-dev", department_id="dept-ti", name="Desarrollador",
                        seniority_level=1, seniority_label="Junior")
        role_hr = Role(id="role-hr", department_id="dept-rrhh", name="Analista RR.HH.",
                       seniority_level=2, seniority_label="Mid")
        db.add_all([role_dev, role_hr])
        db.flush()

        # Dos usuarios: uno con acceso RR.HH. y uno normal
        pw = hash_password("demo123")
        users = [
            User(
                id="user-rrhh", company_id="comp-001",
                department_id="dept-rrhh", role_id="role-hr",
                full_name="Andrea Salcedo", email="andrea.salcedo@techcorp.co",
                hashed_password=pw, system_role="rrhh", status="activo",
                start_date="2024-01-15",
            ),
            User(
                id="user-emp", company_id="comp-001",
                department_id="dept-ti", role_id="role-dev",
                full_name="Carlos Mejía", email="carlos.mejia@techcorp.co",
                hashed_password=pw, system_role="empleado", status="activo",
                start_date="2026-06-01",
            ),
        ]
        db.add_all(users)
        db.commit()

        print("Listo. Usuarios creados (contraseña demo123):")
        print("  - andrea.salcedo@techcorp.co  (RR.HH.)")
        print("  - carlos.mejia@techcorp.co    (empleado)")

    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
