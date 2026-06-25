from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json

from app.db.database import get_db
from app.models.models import (
    EmployeeTask, EmployeePlan, OnboardingPlan, OnboardingQuestion,
    QuizAttempt, QuizAnswer, Document, User,
)
from app.schemas.schemas import (
    EmployeeTaskOut, EmployeePlanDetailOut, EmployeeStepOut,
    QuizPublicOut, QuizSubmit, QuizResultOut,
)
from app.core.dependencies import get_current_user, require_rrhh
from app.services.onboarding import (
    accumulate_step_time, recompute_plan_time, check_plan_completion,
    grade_quiz, reset_plan_on_fail,
)

router = APIRouter(prefix="/api/tasks", tags=["Tareas del empleado"])

# Orden de prioridad de los planes en la vista del empleado
_PLAN_ORDER = {"en_progreso": 0, "sin_empezar": 1, "finalizado": 2, "perdido": 3}


# ─── SERIALIZACIÓN ───────────────────────────────────────────────────────────

def _step_out(db: Session, s: EmployeeTask) -> dict:
    has_quiz = s.category == "cuestionario"
    qcount = 0
    if has_quiz and s.plan_task_id:
        qcount = db.query(OnboardingQuestion).filter(OnboardingQuestion.task_id == s.plan_task_id).count()
    doc_name = None
    if s.document_id:
        doc = db.query(Document).filter(Document.id == s.document_id).first()
        doc_name = doc.name if doc else None
    # Tiempo en vivo: si el cronómetro corre, suma lo transcurrido desde la reanudación
    running_extra = 0
    if s.last_resumed_at:
        running_extra = max(0, int((datetime.utcnow() - s.last_resumed_at).total_seconds()))
    return {
        "id": s.id, "title": s.title, "description": s.description, "category": s.category,
        "status": s.status, "order_index": s.order_index or 0, "day_number": s.day_number,
        "estimated_minutes": s.estimated_minutes or 0,
        "time_spent_seconds": (s.time_spent_seconds or 0) + running_extra,
        "is_running": s.last_resumed_at is not None,
        "completed_at": s.completed_at, "document_id": s.document_id, "document_name": doc_name,
        "has_quiz": has_quiz, "question_count": qcount,
    }


def _owned_step(db: Session, step_id: str, user: User) -> EmployeeTask:
    step = db.query(EmployeeTask).filter(
        EmployeeTask.id == step_id, EmployeeTask.user_id == user.id
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="Paso no encontrado")
    return step


def _ep_of(db: Session, step: EmployeeTask) -> EmployeePlan | None:
    if not step.employee_plan_id:
        return None
    return db.query(EmployeePlan).filter(EmployeePlan.id == step.employee_plan_id).first()


# ─── PLANES DEL EMPLEADO (vista de ejecución) ────────────────────────────────

@router.get("/my-plans", response_model=List[EmployeePlanDetailOut])
def get_my_plans(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    eps = db.query(EmployeePlan).filter(EmployeePlan.user_id == current_user.id).all()
    eps.sort(key=lambda e: (
        _PLAN_ORDER.get(e.status, 9),
        -(e.assigned_at.timestamp() if e.assigned_at else 0),
    ))
    out = []
    for ep in eps:
        steps = db.query(EmployeeTask).filter(
            EmployeeTask.employee_plan_id == ep.id
        ).order_by(EmployeeTask.order_index, EmployeeTask.day_number).all()
        plan = db.query(OnboardingPlan).filter(OnboardingPlan.id == ep.plan_id).first()
        completed = sum(1 for s in steps if s.status == "completada")
        out.append({
            "id": ep.id, "plan_id": ep.plan_id, "plan_name": ep.plan_name,
            "description": plan.description if plan else None,
            "status": ep.status, "attempt_number": ep.attempt_number, "score": ep.score,
            "pass_threshold": ep.pass_threshold or 70,
            "duration_days": plan.duration_days if plan else None,
            "time_spent_seconds": ep.time_spent_seconds or 0,
            "total_steps": len(steps), "completed_steps": completed,
            "assigned_at": ep.assigned_at, "completed_at": ep.completed_at,
            "steps": [_step_out(db, s) for s in steps],
        })
    return out


# ─── CRONÓMETRO DE UN PASO ───────────────────────────────────────────────────

@router.post("/steps/{step_id}/start", response_model=EmployeeStepOut)
def start_step(step_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    step = _owned_step(db, step_id, current_user)
    if step.status == "completada":
        raise HTTPException(status_code=400, detail="El paso ya está completado")
    if not step.last_resumed_at:
        step.last_resumed_at = datetime.utcnow()
    step.status = "en_progreso"
    if not step.started_at:
        step.started_at = datetime.utcnow()
    ep = _ep_of(db, step)
    if ep and ep.status == "sin_empezar":
        ep.status = "en_progreso"
        if not ep.started_at:
            ep.started_at = datetime.utcnow()
    db.commit()
    db.refresh(step)
    return _step_out(db, step)


@router.post("/steps/{step_id}/pause", response_model=EmployeeStepOut)
def pause_step(step_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    step = _owned_step(db, step_id, current_user)
    accumulate_step_time(step)
    ep = _ep_of(db, step)
    if ep:
        recompute_plan_time(db, ep)
    db.commit()
    db.refresh(step)
    return _step_out(db, step)


@router.post("/steps/{step_id}/complete")
def complete_step(step_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    step = _owned_step(db, step_id, current_user)
    if step.category == "cuestionario":
        raise HTTPException(status_code=400, detail="Este paso se completa enviando el cuestionario.")
    accumulate_step_time(step)
    step.status = "completada"
    step.completed_at = datetime.utcnow()
    ep = _ep_of(db, step)
    plan_status = None
    if ep:
        recompute_plan_time(db, ep)
        check_plan_completion(db, ep)
        plan_status = ep.status
    db.commit()
    return {"ok": True, "plan_status": plan_status, "step": _step_out(db, step)}


# ─── CUESTIONARIO ────────────────────────────────────────────────────────────

@router.get("/steps/{step_id}/quiz", response_model=QuizPublicOut)
def get_quiz(step_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    step = _owned_step(db, step_id, current_user)
    if step.category != "cuestionario":
        raise HTTPException(status_code=400, detail="Este paso no es un cuestionario")
    questions = []
    if step.plan_task_id:
        questions = db.query(OnboardingQuestion).filter(
            OnboardingQuestion.task_id == step.plan_task_id
        ).order_by(OnboardingQuestion.order_index).all()
    return {
        "step_id": step.id,
        "title": step.title,
        "questions": [
            {
                "id": q.id, "text": q.text, "qtype": q.qtype,
                "options": [{"id": o.id, "text": o.text} for o in sorted(q.options, key=lambda x: x.order_index)],
            }
            for q in questions
        ],
    }


@router.post("/steps/{step_id}/quiz", response_model=QuizResultOut)
def submit_quiz(
    step_id: str,
    data: QuizSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    step = _owned_step(db, step_id, current_user)
    if step.category != "cuestionario":
        raise HTTPException(status_code=400, detail="Este paso no es un cuestionario")
    if step.status == "completada":
        raise HTTPException(status_code=400, detail="Este cuestionario ya fue aprobado")
    ep = _ep_of(db, step)
    if not ep:
        raise HTTPException(status_code=400, detail="El paso no pertenece a un plan activo")

    accumulate_step_time(step)  # detener el cronómetro del paso
    score, correct, total, detail = grade_quiz(db, step, data.answers)
    threshold = ep.pass_threshold or 70
    passed = score >= threshold

    # Historial del intento
    prev = db.query(QuizAttempt).filter(
        QuizAttempt.employee_plan_id == ep.id, QuizAttempt.employee_task_id == step.id
    ).count()
    attempt = QuizAttempt(
        employee_plan_id=ep.id, employee_task_id=step.id, user_id=current_user.id,
        score=score, passed=passed, attempt_number=prev + 1,
        time_spent_seconds=step.time_spent_seconds or 0,
    )
    db.add(attempt)
    db.flush()
    for q, selected, is_correct in detail:
        db.add(QuizAnswer(
            attempt_id=attempt.id, question_id=q.id, question_text=q.text,
            category=q.category, selected_option_ids=json.dumps(list(selected)),
            is_correct=is_correct,
        ))

    if passed:
        step.status = "completada"
        step.completed_at = datetime.utcnow()
        recompute_plan_time(db, ep)
        check_plan_completion(db, ep)
        db.commit()
        return QuizResultOut(
            score=score, passed=True, threshold=threshold, correct_count=correct,
            total=total, plan_status=ep.status, reset=False, new_plan_id=None,
        )

    # Falló → se pierde el plan y se crea un intento nuevo
    new_ep = reset_plan_on_fail(db, ep, score)
    db.commit()
    return QuizResultOut(
        score=score, passed=False, threshold=threshold, correct_count=correct,
        total=total, plan_status="perdido", reset=True,
        new_plan_id=new_ep.id if new_ep else None,
    )


# ─── COMPATIBILIDAD / RR.HH. ─────────────────────────────────────────────────

@router.get("/my", response_model=List[EmployeeTaskOut])
def get_my_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(EmployeeTask).filter(
        EmployeeTask.user_id == current_user.id
    ).order_by(EmployeeTask.order_index, EmployeeTask.day_number).all()


@router.patch("/{task_id}/complete")
def complete_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(EmployeeTask).filter(
        EmployeeTask.id == task_id, EmployeeTask.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task.category == "cuestionario":
        raise HTTPException(status_code=400, detail="Este paso se completa enviando el cuestionario.")
    accumulate_step_time(task)
    task.status = "completada"
    task.completed_at = datetime.utcnow()
    ep = _ep_of(db, task)
    if ep:
        recompute_plan_time(db, ep)
        check_plan_completion(db, ep)
    db.commit()
    return {"mensaje": "Tarea completada"}


VALID_STATUSES = {"pendiente", "en_progreso", "completada", "bloqueada"}


@router.patch("/{task_id}/status")
def update_task_status(
    task_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Valores permitidos: {', '.join(sorted(VALID_STATUSES))}",
        )
    task = db.query(EmployeeTask).filter(
        EmployeeTask.id == task_id, EmployeeTask.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    task.status = status
    db.commit()
    return {"mensaje": f"Estado actualizado a {status}"}


@router.get("/user/{user_id}", response_model=List[EmployeeTaskOut])
def get_user_tasks(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    target = db.query(User).filter(
        User.id == user_id, User.company_id == current_user.company_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return db.query(EmployeeTask).filter(
        EmployeeTask.user_id == user_id
    ).order_by(EmployeeTask.order_index, EmployeeTask.day_number).all()
