from app.db.database import SessionLocal
from app.models.models import (
    Company, Department, Role, User, OnboardingPlan, OnboardingTask,
    EmployeeTask, PayrollConcept, PayrollPeriod, Payslip, PayslipItem
)
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

        # Usuarios (expediente RR.HH. completo para métricas realistas)
        pw = hash_password("demo123")
        users = [
            # ── Empleados en onboarding ──
            User(
                id="user-001", company_id="comp-001",
                department_id="dept-001", role_id="role-001",
                full_name="Carlos Mejía", email="carlos.mejia@techcorp.co",
                hashed_password=pw, system_role="empleado", status="onboarding",
                start_date="2026-03-25", onboarding_day=5, onboarding_total_days=15,
                document_id="1018456321", gender="masculino", birth_date="1998-07-12",
                phone="3104567890", address="Cra 45 #23-10, Bogotá",
                marital_status="soltero", num_children=0, contract_type="indefinido",
                base_salary=2800000, bank_name="Bancolombia", bank_account="12345678901",
            ),
            User(
                id="user-002", company_id="comp-001",
                department_id="dept-002", role_id="role-004",
                full_name="Laura Torres", email="laura.torres@techcorp.co",
                hashed_password=pw, system_role="empleado", status="onboarding",
                start_date="2026-03-29", onboarding_day=1, onboarding_total_days=10,
                document_id="1022789456", gender="femenino", birth_date="1996-02-28",
                phone="3209871234", address="Calle 80 #12-34, Bogotá",
                marital_status="union_libre", num_children=1, contract_type="fijo",
                base_salary=2600000, bank_name="Davivienda", bank_account="98765432109",
            ),
            User(
                id="user-003", company_id="comp-001",
                department_id="dept-004", role_id="role-006",
                full_name="Sebastián Ríos", email="sebastian.rios@techcorp.co",
                hashed_password=pw, system_role="empleado", status="onboarding",
                start_date="2026-03-20", onboarding_day=10, onboarding_total_days=12,
                document_id="1015223344", gender="masculino", birth_date="1999-11-05",
                phone="3001122334", address="Av 68 #45-67, Bogotá",
                marital_status="soltero", num_children=0, contract_type="fijo",
                base_salary=2400000, bank_name="Bancolombia", bank_account="11223344556",
            ),
            # ── Empleados activos ──
            User(
                id="user-004", company_id="comp-001",
                department_id="dept-001", role_id="role-002",
                full_name="Daniela Vargas", email="daniela.vargas@techcorp.co",
                hashed_password=pw, system_role="empleado", status="activo",
                start_date="2024-01-15", onboarding_day=15, onboarding_total_days=15,
                document_id="1019887766", gender="femenino", birth_date="1992-05-19",
                phone="3115566778", address="Cra 7 #100-20, Bogotá",
                marital_status="casado", num_children=2, contract_type="indefinido",
                base_salary=6500000, bank_name="BBVA", bank_account="22334455667",
            ),
            User(
                id="user-005", company_id="comp-001",
                department_id="dept-001", role_id="role-003",
                full_name="Andrés Castaño", email="andres.castano@techcorp.co",
                hashed_password=pw, system_role="empleado", status="activo",
                start_date="2022-06-01", onboarding_day=15, onboarding_total_days=15,
                document_id="80123456", gender="masculino", birth_date="1988-09-30",
                phone="3124433221", address="Calle 134 #7-83, Bogotá",
                marital_status="casado", num_children=3, contract_type="indefinido",
                base_salary=9800000, bank_name="Bancolombia", bank_account="33445566778",
            ),
            User(
                id="user-006", company_id="comp-001",
                department_id="dept-002", role_id="role-004",
                full_name="Valentina Gómez", email="valentina.gomez@techcorp.co",
                hashed_password=pw, system_role="empleado", status="activo",
                start_date="2023-09-12", onboarding_day=15, onboarding_total_days=15,
                document_id="1023445566", gender="femenino", birth_date="1995-12-08",
                phone="3137788990", address="Cra 50 #80-15, Bogotá",
                marital_status="soltero", num_children=0, contract_type="indefinido",
                base_salary=3500000, bank_name="Nequi", bank_account="3137788990",
            ),
            User(
                id="user-007", company_id="comp-001",
                department_id="dept-004", role_id="role-006",
                full_name="Juan Pablo Mora", email="juanpablo.mora@techcorp.co",
                hashed_password=pw, system_role="empleado", status="activo",
                start_date="2024-03-04", onboarding_day=15, onboarding_total_days=15,
                document_id="1026778899", gender="masculino", birth_date="1994-04-22",
                phone="3148899001", address="Av Suba #110-40, Bogotá",
                marital_status="union_libre", num_children=1, contract_type="fijo",
                base_salary=3000000, bank_name="Davivienda", bank_account="44556677889",
            ),
            User(
                id="user-008", company_id="comp-001",
                department_id="dept-004", role_id="role-006",
                full_name="Camila Restrepo", email="camila.restrepo@techcorp.co",
                hashed_password=pw, system_role="empleado", status="activo",
                start_date="2023-02-20", onboarding_day=15, onboarding_total_days=15,
                document_id="1098112233", gender="femenino", birth_date="1993-08-14",
                phone="3159900112", address="Calle 26 #68-90, Bogotá",
                marital_status="divorciado", num_children=1, contract_type="indefinido",
                base_salary=3200000, bank_name="Bancolombia", bank_account="55667788990",
            ),
            User(
                id="user-009", company_id="comp-001",
                department_id="dept-005", role_id="role-007",
                full_name="Ricardo Lozano", email="ricardo.lozano@techcorp.co",
                hashed_password=pw, system_role="gerencia", status="activo",
                start_date="2021-01-10", onboarding_day=15, onboarding_total_days=15,
                document_id="79556644", gender="masculino", birth_date="1980-03-17",
                phone="3001234455", address="Cra 11 #93-45, Bogotá",
                marital_status="casado", num_children=2, contract_type="indefinido",
                base_salary=15000000, bank_name="BBVA", bank_account="66778899001",
            ),
            User(
                id="user-010", company_id="comp-001",
                department_id="dept-002", role_id="role-004",
                full_name="Felipe Naranjo", email="felipe.naranjo@techcorp.co",
                hashed_password=pw, system_role="empleado", status="inactivo",
                start_date="2022-11-01", onboarding_day=15, onboarding_total_days=15,
                document_id="1011334477", gender="masculino", birth_date="1991-06-25",
                phone="3162233445", address="Calle 72 #10-34, Bogotá",
                marital_status="soltero", num_children=0, contract_type="prestacion_servicios",
                base_salary=0, bank_name="Nequi", bank_account="3162233445",
                is_active=False,
            ),
            # ── RR.HH. ──
            User(
                id="user-rrhh", company_id="comp-001",
                department_id="dept-003", role_id="role-005",
                full_name="Andrea Salcedo", email="andrea.salcedo@techcorp.co",
                hashed_password=pw, system_role="rrhh", status="activo",
                start_date="2023-03-01", onboarding_day=15, onboarding_total_days=15,
                document_id="52998877", gender="femenino", birth_date="1990-10-02",
                phone="3171122334", address="Cra 15 #88-21, Bogotá",
                marital_status="casado", num_children=2, contract_type="indefinido",
                base_salary=5200000, bank_name="Bancolombia", bank_account="77889900112",
            ),
            User(
                id="user-rrhh2", company_id="comp-001",
                department_id="dept-003", role_id="role-005",
                full_name="Mariana Ospina", email="mariana.ospina@techcorp.co",
                hashed_password=pw, system_role="rrhh", status="activo",
                start_date="2024-05-15", onboarding_day=15, onboarding_total_days=15,
                document_id="1024556677", gender="femenino", birth_date="1997-01-21",
                phone="3183344556", address="Calle 53 #25-60, Bogotá",
                marital_status="soltero", num_children=0, contract_type="fijo",
                base_salary=3400000, bank_name="Davivienda", bank_account="88990011223",
            ),
        ]
        for u in users:
            db.add(u)
        db.flush()

        # Conceptos de nómina (genéricos, definidos por RR.HH. — editables)
        concepts = [
            PayrollConcept(id="con-001", company_id="comp-001", name="Auxilio de transporte",
                           type="devengado", calc_type="fijo", value=200000,
                           description="Auxilio mensual de transporte"),
            PayrollConcept(id="con-002", company_id="comp-001", name="Bonificación",
                           type="devengado", calc_type="porcentaje", value=5,
                           description="Bonificación equivalente al 5% del salario base"),
            PayrollConcept(id="con-003", company_id="comp-001", name="Aporte salud",
                           type="deduccion", calc_type="porcentaje", value=4,
                           description="Deducción del 4% del salario base"),
            PayrollConcept(id="con-004", company_id="comp-001", name="Aporte pensión",
                           type="deduccion", calc_type="porcentaje", value=4,
                           description="Deducción del 4% del salario base"),
            PayrollConcept(id="con-005", company_id="comp-001", name="Aporte patronal salud",
                           type="aporte_patronal", calc_type="porcentaje", value=8.5,
                           description="Aporte del empleador a salud"),
            PayrollConcept(id="con-006", company_id="comp-001", name="Provisión cesantías",
                           type="provision", calc_type="porcentaje", value=8.33,
                           description="Provisión mensual de cesantías"),
        ]
        for c in concepts:
            db.add(c)
        db.flush()

        # Período de nómina de ejemplo ya liquidado (mayo 2026)
        active_concepts = [c for c in concepts if c.is_active]
        payroll_users = [u for u in users if u.is_active and (u.base_salary or 0) > 0]

        period = PayrollPeriod(
            id="period-001", company_id="comp-001", name="Mayo 2026",
            period_start="2026-05-01", period_end="2026-05-31", status="pagada",
            kind="nomina", factor=1.0, days=30, month_key="2026-05",
        )
        db.add(period)
        db.flush()

        g_dev = g_ded = g_apo = g_net = 0.0
        for emp in payroll_users:
            base = emp.base_salary or 0
            slip = Payslip(period_id="period-001", user_id=emp.id,
                           employee_name=emp.full_name, base_salary=base)
            db.add(slip)
            db.flush()
            db.add(PayslipItem(payslip_id=slip.id, concept_id=None,
                               concept_name="Salario base", type="devengado", amount=round(base, 2)))
            t_dev, t_ded, t_apo = round(base, 2), 0.0, 0.0
            for c in active_concepts:
                amount = round(base * c.value / 100, 2) if c.calc_type == "porcentaje" else round(c.value, 2)
                db.add(PayslipItem(payslip_id=slip.id, concept_id=c.id,
                                   concept_name=c.name, type=c.type, amount=amount))
                if c.type == "devengado":
                    t_dev += amount
                elif c.type == "deduccion":
                    t_ded += amount
                else:
                    t_apo += amount
            net = round(t_dev - t_ded, 2)
            slip.total_devengado, slip.total_deduccion = round(t_dev, 2), round(t_ded, 2)
            slip.total_aportes, slip.net_pay = round(t_apo, 2), net
            g_dev += t_dev; g_ded += t_ded; g_apo += t_apo; g_net += net

        period.total_devengado = round(g_dev, 2)
        period.total_deduccion = round(g_ded, 2)
        period.total_aportes = round(g_apo, 2)
        period.total_neto = round(g_net, 2)
        period.employee_count = len(payroll_users)
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

        # Tareas asignadas a los empleados en onboarding (instancias reales del plan).
        # Carlos (user-001) va por el día 5: primeros días completados, resto pendiente.
        carlos_tasks = [
            ("Leer manual de empleados", "lectura", 1, "completada"),
            ("Reunión de bienvenida con RR.HH.", "reunion", 1, "completada"),
            ("Configurar entorno de desarrollo", "configuracion", 2, "completada"),
            ("Reunión con Tech Lead", "reunion", 2, "completada"),
            ("Revisar política de seguridad IT", "lectura", 3, "en_progreso"),
            ("Primer PR de prueba", "entregable", 5, "pendiente"),
        ]
        for title, cat, day, status in carlos_tasks:
            db.add(EmployeeTask(user_id="user-001", title=title, category=cat,
                                day_number=day, status=status))

        # Laura (user-002) recién empieza: casi todo pendiente.
        laura_tasks = [
            ("Leer manual de empleados", "lectura", 1, "completada"),
            ("Reunión de bienvenida con RR.HH.", "reunion", 1, "pendiente"),
            ("Configurar herramientas de marketing", "configuracion", 2, "pendiente"),
        ]
        for title, cat, day, status in laura_tasks:
            db.add(EmployeeTask(user_id="user-002", title=title, category=cat,
                                day_number=day, status=status))

        # Sebastián (user-003) casi termina.
        sebas_tasks = [
            ("Leer manual de empleados", "lectura", 1, "completada"),
            ("Capacitación de producto", "lectura", 3, "completada"),
            ("Acompañar primera llamada de ventas", "entregable", 8, "completada"),
            ("Cierre de onboarding con líder", "reunion", 12, "pendiente"),
        ]
        for title, cat, day, status in sebas_tasks:
            db.add(EmployeeTask(user_id="user-003", title=title, category=cat,
                                day_number=day, status=status))

        db.commit()
        print("Datos iniciales creados exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"Error en seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()