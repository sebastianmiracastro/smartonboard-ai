"""Crea un plan de onboarding de EJEMPLO (con pasos y un cuestionario) y lo asigna
a un empleado en onboarding, para poder probar el flujo de "Mi plan" en el portal.

Idempotente: si el plan de ejemplo ya existe no lo duplica, y solo asigna si el
empleado no lo tiene.

Uso:
    cd backend
    venv\\Scripts\\activate
    python -m app.db.seed_demo_plan
"""
from app.db.database import SessionLocal
from app.models.models import (
    OnboardingPlan, OnboardingTask, OnboardingQuestion, OnboardingQuestionOption, User,
)
from app.services.onboarding import assign_plan_to_user, has_active_assignment

COMPANY_ID = "comp-001"
DEMO_PLAN_NAME = "Onboarding de ejemplo (con evaluación)"
ASSIGN_TO_EMAIL = "carlos.mejia@techcorp.co"  # empleado demo en onboarding


def _build_plan(db) -> OnboardingPlan:
    plan = OnboardingPlan(
        company_id=COMPANY_ID, name=DEMO_PLAN_NAME,
        description="Plan de muestra para probar pasos y cuestionario calificado.",
        target_role_id="role-001", duration_days=10, auto_assign=False, pass_threshold=60,
    )
    db.add(plan)
    db.flush()

    # Pasos normales (se completan con el cronómetro)
    normales = [
        ("Leer el manual de bienvenida", "lectura", 1, 20),
        ("Reunión de presentación con tu líder", "reunion", 1, 30),
        ("Configurar tu entorno de trabajo", "tarea", 2, 45),
    ]
    for i, (title, cat, day, mins) in enumerate(normales):
        db.add(OnboardingTask(
            plan_id=plan.id, title=title, category=cat, day_number=day,
            order_index=i, estimated_minutes=mins,
        ))

    # Paso tipo cuestionario (se aprueba respondiendo)
    quiz = OnboardingTask(
        plan_id=plan.id, title="Evaluación de comprensión", category="cuestionario",
        day_number=3, order_index=len(normales), estimated_minutes=15,
    )
    db.add(quiz)
    db.flush()

    preguntas = [
        ("¿A quién acudes para solicitar vacaciones?", "single", "procesos",
         [("A Recursos Humanos", True), ("A un compañero cualquiera", False), ("A nadie", False)]),
        ("¿Cuáles de estas son herramientas de trabajo?", "multiple", "herramientas",
         [("Jira", True), ("Git", True), ("La cafetera", False)]),
        ("¿El plan de onboarding es obligatorio?", "single", "cultura",
         [("Sí, debo completarlo", True), ("No, es opcional", False)]),
    ]
    for qi, (text, qtype, cat, opts) in enumerate(preguntas):
        q = OnboardingQuestion(task_id=quiz.id, text=text, qtype=qtype, category=cat, order_index=qi)
        db.add(q)
        db.flush()
        for oi, (otext, correct) in enumerate(opts):
            db.add(OnboardingQuestionOption(question_id=q.id, text=otext, is_correct=correct, order_index=oi))

    return plan


def seed_demo_plan():
    db = SessionLocal()
    try:
        plan = db.query(OnboardingPlan).filter(
            OnboardingPlan.company_id == COMPANY_ID,
            OnboardingPlan.name == DEMO_PLAN_NAME,
        ).first()
        if plan:
            print("El plan de ejemplo ya existe; no se duplica.")
        else:
            plan = _build_plan(db)
            db.commit()
            print(f"✓ Plan de ejemplo creado: '{DEMO_PLAN_NAME}' (3 pasos + 1 cuestionario de 3 preguntas).")

        user = db.query(User).filter(User.email == ASSIGN_TO_EMAIL).first()
        if not user:
            print(f"⚠ No se encontró el empleado {ASSIGN_TO_EMAIL}; no se asignó.")
            return
        if has_active_assignment(db, user.id, plan.id):
            print(f"El empleado {user.full_name} ya tenía el plan asignado.")
        else:
            assign_plan_to_user(db, plan, user)
            db.commit()
            print(f"✓ Plan asignado a {user.full_name} ({user.email}).")
        print("\nAhora inicia sesión en el portal como ese empleado (contraseña demo123),")
        print("entra a 'Mi plan' y verás el botón 'Responder' en el cuestionario.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_plan()
