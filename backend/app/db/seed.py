from app.db.database import SessionLocal
from app.models.models import Company, Department, Role, User, OnboardingPlan, OnboardingTask
from app.core.security import hash_password

def seed():
    db = SessionLocal()
    
    try:
        # Verificar si ya hay datos
        if db.query(Company).first():
            print("Base de datos ya tiene datos, omitiendo seed.")
            return

        print("Creando datos iniciales...")

        # Empresa
        company = Company(
            id="comp-001",
            name="TechCorp S.A.S.",
            slug="techcorp",
            industry="Tecnología"
        )
        db.add(company)
        db.flush()

        # Departamentos
        dept_ing = Department(id="dept-001", company_id="comp-001", name="Ingeniería", description="Desarrollo de producto", is_rrhh=False, is_gerencia=False, color="#6366f1")
        dept_mkt = Department(id="dept-002", company_id="comp-001", name="Marketing", description="Comunicaciones y marca", is_rrhh=False, is_gerencia=False, color="#ec4899")
        dept_rrhh = Department(id="dept-003", company_id="comp-001", name="Recursos Humanos", description="Gestión del talento", is_rrhh=True, is_gerencia=False, color="#10b981")
        dept_ventas = Department(id="dept-004", company_id="comp-001", name="Ventas", description="Gestión comercial", is_rrhh=False, is_gerencia=False, color="#f59e0b")
        dept_ger = Department(id="dept-005", company_id="comp-001", name="Gerencia", description="Alta dirección", is_rrhh=False, is_gerencia=True, color="#8b5cf6")

        for d in [dept_ing, dept_mkt, dept_rrhh, dept_ventas, dept_ger]:
            db.add(d)
        db.flush()

        # Roles
        roles = [
            Role(id="role-001", department_id="dept-001", name="Desarrollador Junior", seniority_level=1, seniority_label="Junior"),
            Role(id="role-002", department_id="dept-001", name="Desarrollador Senior", seniority_level=3, seniority_label="Senior"),
            Role(id="role-003", department_id="dept-001", name="Tech Lead", seniority_level=4, seniority_label="Lead"),
            Role(id="role-004", department_id="dept-002", name="Analista de Marketing", seniority_level=1, seniority_label="Junior"),
            Role(id="role-005", department_id="dept-003", name="Analista RR.HH.", seniority_level=2, seniority_label="Mid"),
            Role(id="role-006", department_id="dept-004", name="Ejecutivo de Ventas", seniority_level=1, seniority_label="Junior"),
            Role(id="role-007", department_id="dept-005", name="Director General", seniority_level=4, seniority_label="Director"),
        ]
        for r in roles:
            db.add(r)
        db.flush()

        # Usuarios
        users = [
            User(
                id="user-001", company_id="comp-001",
                department_id="dept-001", role_id="role-001",
                full_name="Carlos Mejía", email="carlos.mejia@techcorp.co",
                hashed_password=hash_password("demo123"),
                system_role="empleado", status="onboarding",
                start_date="2026-03-25", onboarding_day=5, onboarding_total_days=15
            ),
            User(
                id="user-002", company_id="comp-001",
                department_id="dept-002", role_id="role-004",
                full_name="Laura Torres", email="laura.torres@techcorp.co",
                hashed_password=hash_password("demo123"),
                system_role="empleado", status="onboarding",
                start_date="2026-03-29", onboarding_day=1, onboarding_total_days=10
            ),
            User(
                id="user-003", company_id="comp-001",
                department_id="dept-004", role_id="role-006",
                full_name="Sebastián Ríos", email="sebastian.rios@techcorp.co",
                hashed_password=hash_password("demo123"),
                system_role="empleado", status="onboarding",
                start_date="2026-03-20", onboarding_day=10, onboarding_total_days=12
            ),
            User(
                id="user-rrhh", company_id="comp-001",
                department_id="dept-003", role_id="role-005",
                full_name="Andrea Salcedo", email="andrea.salcedo@techcorp.co",
                hashed_password=hash_password("demo123"),
                system_role="rrhh", status="activo",
                start_date="2023-03-01", onboarding_day=15, onboarding_total_days=15
            ),
        ]
        for u in users:
            db.add(u)
        db.flush()

        # Plan de onboarding
        plan = OnboardingPlan(
            id="plan-001", company_id="comp-001",
            name="Onboarding Ingeniería Junior",
            description="Plan para desarrolladores junior",
            target_role_id="role-001",
            target_department_id="dept-001",
            duration_days=15
        )
        db.add(plan)
        db.flush()

        # Tareas del plan
        tasks = [
            OnboardingTask(plan_id="plan-001", title="Leer manual de empleados", day_number=1, category="lectura", estimated_minutes=60),
            OnboardingTask(plan_id="plan-001", title="Reunión de bienvenida con RR.HH.", day_number=1, category="reunion", estimated_minutes=30),
            OnboardingTask(plan_id="plan-001", title="Configurar entorno de desarrollo", day_number=2, category="configuracion", estimated_minutes=90),
            OnboardingTask(plan_id="plan-001", title="Reunión con Tech Lead", day_number=2, category="reunion", estimated_minutes=45),
            OnboardingTask(plan_id="plan-001", title="Revisar política de seguridad IT", day_number=3, category="lectura", estimated_minutes=45),
            OnboardingTask(plan_id="plan-001", title="Primer PR de prueba", day_number=5, category="entregable", estimated_minutes=120),
        ]
        for t in tasks:
            db.add(t)

        db.commit()
        print("Datos iniciales creados exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()