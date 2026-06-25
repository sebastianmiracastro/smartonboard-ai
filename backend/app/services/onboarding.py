"""Asignación de planes de onboarding a empleados.

Centraliza la creación de la instancia (`EmployeePlan` + `EmployeeTask` por paso)
a partir de una plantilla `OnboardingPlan`, reutilizada por la asignación manual
(endpoint) y la automática (al crear un empleado o cambiarle el rol).

Las funciones NO hacen commit: añaden/flushean y el endpoint que llama decide
cuándo confirmar la transacción.
"""
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.models import (
    OnboardingPlan, OnboardingTask, OnboardingQuestion, EmployeePlan, EmployeeTask,
    QuizAttempt, RRHHAlert, User,
)


# Estados de un EmployeePlan que cuentan como "ya asignado" (no se duplica)
ACTIVE_PLAN_STATES = ("sin_empezar", "en_progreso", "finalizado")

# Tras este nº de intentos fallidos del mismo plan se alerta a RR.HH.
MAX_PLAN_ATTEMPTS = 3


def has_active_assignment(db: Session, user_id: str, plan_id: str) -> bool:
    """¿El usuario ya tiene una instancia no perdida de este plan?"""
    return db.query(EmployeePlan).filter(
        EmployeePlan.user_id == user_id,
        EmployeePlan.plan_id == plan_id,
        EmployeePlan.status.in_(ACTIVE_PLAN_STATES),
    ).first() is not None


def _next_attempt_number(db: Session, user_id: str, plan_id: str) -> int:
    n = db.query(EmployeePlan).filter(
        EmployeePlan.user_id == user_id,
        EmployeePlan.plan_id == plan_id,
    ).count()
    return n + 1


def assign_plan_to_user(db: Session, plan: OnboardingPlan, user: User) -> EmployeePlan:
    """Crea una instancia del plan para el empleado (un intento) con todos sus
    pasos en estado 'pendiente'. Pone al usuario en estado 'onboarding'."""
    ep = EmployeePlan(
        company_id=user.company_id,
        user_id=user.id,
        plan_id=plan.id,
        plan_name=plan.name,
        status="sin_empezar",
        attempt_number=_next_attempt_number(db, user.id, plan.id),
        pass_threshold=plan.pass_threshold if plan.pass_threshold is not None else 70,
    )
    db.add(ep)
    db.flush()  # para tener ep.id

    steps = (
        db.query(OnboardingTask)
        .filter(OnboardingTask.plan_id == plan.id)
        .order_by(OnboardingTask.order_index, OnboardingTask.day_number)
        .all()
    )
    for t in steps:
        db.add(EmployeeTask(
            user_id=user.id,
            employee_plan_id=ep.id,
            plan_task_id=t.id,
            title=t.title,
            description=t.description,
            category=t.category,
            status="pendiente",
            day_number=t.day_number,
            order_index=t.order_index or 0,
            estimated_minutes=t.estimated_minutes or 0,
            document_id=t.document_id,
        ))

    # El empleado entra (o vuelve) a onboarding
    user.status = "onboarding"
    user.onboarding_plan_id = plan.id
    if plan.duration_days:
        user.onboarding_total_days = plan.duration_days

    return ep


def auto_assign_plans_for_user(db: Session, user: User) -> List[EmployeePlan]:
    """Asigna los planes marcados como automáticos cuyo cargo objetivo coincide
    con el rol del empleado. No duplica los ya asignados."""
    assigned: List[EmployeePlan] = []
    if not user.role_id:
        return assigned

    plans = db.query(OnboardingPlan).filter(
        OnboardingPlan.company_id == user.company_id,
        OnboardingPlan.auto_assign == True,   # noqa: E712
        OnboardingPlan.is_active == True,     # noqa: E712
        OnboardingPlan.target_role_id == user.role_id,
    ).all()

    for plan in plans:
        if has_active_assignment(db, user.id, plan.id):
            continue
        assigned.append(assign_plan_to_user(db, plan, user))

    return assigned


# ─── EJECUCIÓN: CRONÓMETRO, CALIFICACIÓN, ESTADOS ────────────────────────────

def accumulate_step_time(step: EmployeeTask) -> None:
    """Suma el tiempo transcurrido desde la última reanudación y detiene el reloj."""
    if step.last_resumed_at:
        delta = (datetime.utcnow() - step.last_resumed_at).total_seconds()
        step.time_spent_seconds = (step.time_spent_seconds or 0) + max(0, int(delta))
        step.last_resumed_at = None


def _plan_steps(db: Session, ep: EmployeePlan) -> List[EmployeeTask]:
    return db.query(EmployeeTask).filter(EmployeeTask.employee_plan_id == ep.id).all()


def recompute_plan_time(db: Session, ep: EmployeePlan) -> None:
    ep.time_spent_seconds = sum((s.time_spent_seconds or 0) for s in _plan_steps(db, ep))


def pause_running_steps(db: Session, user: User) -> None:
    """Pausa el cronómetro de los pasos en curso (p.ej. si el empleado queda inactivo)."""
    running = db.query(EmployeeTask).filter(
        EmployeeTask.user_id == user.id,
        EmployeeTask.last_resumed_at.isnot(None),
    ).all()
    for s in running:
        accumulate_step_time(s)


def check_user_onboarding_complete(db: Session, user: User) -> None:
    """Si el empleado no tiene planes activos y completó al menos uno → activo."""
    db.flush()  # la sesión usa autoflush=False; asegurar que los cambios de estado se vean en los conteos
    active = db.query(EmployeePlan).filter(
        EmployeePlan.user_id == user.id,
        EmployeePlan.status.in_(("sin_empezar", "en_progreso")),
    ).count()
    finalized = db.query(EmployeePlan).filter(
        EmployeePlan.user_id == user.id,
        EmployeePlan.status == "finalizado",
    ).count()
    if active == 0 and finalized > 0:
        user.status = "activo"


def check_plan_completion(db: Session, ep: EmployeePlan) -> bool:
    """Si todos los pasos están completados marca el plan como finalizado (válido)."""
    steps = _plan_steps(db, ep)
    if not steps or not all(s.status == "completada" for s in steps):
        return False

    ep.status = "finalizado"
    ep.completed_at = datetime.utcnow()
    recompute_plan_time(db, ep)

    # Nota del plan = promedio de la mejor nota por cuestionario (si hubo)
    attempts = db.query(QuizAttempt).filter(QuizAttempt.employee_plan_id == ep.id).all()
    best_by_step: dict = {}
    for a in attempts:
        best_by_step[a.employee_task_id] = max(best_by_step.get(a.employee_task_id, 0), a.score)
    ep.score = round(sum(best_by_step.values()) / len(best_by_step), 1) if best_by_step else None

    user = db.query(User).filter(User.id == ep.user_id).first()
    if user:
        check_user_onboarding_complete(db, user)
    return True


def grade_quiz(db: Session, step: EmployeeTask, answers: List) -> Tuple[float, int, int, list]:
    """Califica un cuestionario. Devuelve (nota 0-100, aciertos, total, detalle).

    `answers` = lista de objetos con .question_id y .selected_option_ids.
    """
    questions = []
    if step.plan_task_id:
        questions = db.query(OnboardingQuestion).filter(
            OnboardingQuestion.task_id == step.plan_task_id
        ).order_by(OnboardingQuestion.order_index).all()

    total = len(questions)
    ans_map = {a.question_id: set(a.selected_option_ids or []) for a in answers}

    correct_count = 0
    detail = []  # (question, selected_set, is_correct)
    for q in questions:
        correct_ids = {o.id for o in q.options if o.is_correct}
        selected = ans_map.get(q.id, set())
        is_correct = bool(selected) and selected == correct_ids
        if is_correct:
            correct_count += 1
        detail.append((q, selected, is_correct))

    score = round(correct_count / total * 100, 1) if total else 0.0
    return score, correct_count, total, detail


def reset_plan_on_fail(db: Session, ep: EmployeePlan, score: float) -> Optional[EmployeePlan]:
    """Marca el intento como 'perdido' y crea un intento nuevo del mismo plan
    (todos los pasos en pendiente). Alerta a RR.HH. si hay demasiados intentos."""
    ep.status = "perdido"
    ep.score = score
    ep.completed_at = datetime.utcnow()
    recompute_plan_time(db, ep)

    if ep.attempt_number >= MAX_PLAN_ATTEMPTS:
        db.add(RRHHAlert(
            company_id=ep.company_id,
            user_id=ep.user_id,
            motivo=(
                f"El empleado no aprobó el plan '{ep.plan_name}' tras "
                f"{ep.attempt_number} intentos (última nota {score:.0f}/100). "
                f"Requiere acompañamiento."
            ),
        ))

    plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == ep.plan_id).first()
    user = db.query(User).filter(User.id == ep.user_id).first()
    if plan and user:
        return assign_plan_to_user(db, plan, user)
    return None
