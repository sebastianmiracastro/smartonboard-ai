"""Seed MÍNIMO: una empresa, 2 departamentos (RR.HH. y TI) y UN solo usuario:
la Directora de RR.HH. Sin empleados, documentos, tareas, planes ni nómina.
La app arranca casi limpia y RR.HH. crea el resto de usuarios desde la UI.

Uso (sobre una BD vacía):
    cd backend
    venv\\Scripts\\activate
    python -m app.db.seed

Para reestablecer la BD desde cero y volver a sembrar, usar en su lugar:
    python -m app.db.reset
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
        company = Company(id="comp-001", name="NovaTech Solutions S.A.S", slug="novatech", industry="Tecnología")
        db.add(company)
        db.flush()

        # Departamentos: RR.HH. y Gerencia
        dept_rrhh = Department(id="dept-rrhh", company_id="comp-001", name="Recursos Humanos",
                               description="Gestión del talento", is_rrhh=True, is_gerencia=False, color="#10b981")
        dept_ger = Department(id="dept-gerencia", company_id="comp-001", name="Gerencia",
                              description="Dirección general", is_rrhh=False, is_gerencia=True, color="#6d5cff")
        db.add_all([dept_rrhh, dept_ger])
        db.flush()

        # Cargos
        role_hr = Role(id="role-hr", department_id="dept-rrhh", name="Directora de RR.HH.",
                       seniority_level=4, seniority_label="Director")
        role_ger = Role(id="role-gerente", department_id="dept-gerencia", name="Gerente General",
                        seniority_level=4, seniority_label="Director")
        db.add_all([role_hr, role_ger])
        db.flush()

        # Usuarios: Directora de RR.HH. y Gerente General (para probar los 3 niveles de acceso)
        pw = hash_password("demo123")
        users = [
            User(
                id="user-rrhh", company_id="comp-001",
                department_id="dept-rrhh", role_id="role-hr",
                full_name="Lucía Hernández", email="lucia.hernandez@novatech.co",
                hashed_password=pw, system_role="rrhh", status="activo",
                start_date="2024-01-15",
            ),
            User(
                id="user-gerencia", company_id="comp-001",
                department_id="dept-gerencia", role_id="role-gerente",
                full_name="Alejandro Cárdenas", email="alejandro.cardenas@novatech.co",
                hashed_password=pw, system_role="gerencia", status="activo",
                start_date="2023-06-01",
            ),
        ]
        db.add_all(users)
        db.commit()

        print("Listo. Usuarios creados (contraseña demo123):")
        print("  - lucia.hernandez@novatech.co    (RR.HH. — Directora)")
        print("  - alejandro.cardenas@novatech.co (Gerencia — Gerente General)")

    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
