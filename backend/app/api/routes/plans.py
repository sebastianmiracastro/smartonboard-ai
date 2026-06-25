from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import (
    OnboardingPlan, OnboardingTask, OnboardingQuestion, OnboardingQuestionOption,
    EmployeePlan, Document, User,
)
from app.schemas.schemas import (
    OnboardingPlanCreate, OnboardingPlanUpdate, OnboardingPlanOut,
    OnboardingTaskCreate, OnboardingTaskUpdate, OnboardingTaskOut,
    QuestionCreate, AssignPlanRequest, EmployeePlanOut,
)
from app.core.dependencies import get_current_user, require_rrhh
from app.services.onboarding import assign_plan_to_user, has_active_assignment

router = APIRouter(prefix="/api/plans", tags=["Planes de onboarding"])


# ─── SERIALIZADORES ──────────────────────────────────────────────────────────

def _serialize_option(o: OnboardingQuestionOption) -> dict:
    return {"id": o.id, "text": o.text, "is_correct": o.is_correct, "order_index": o.order_index}


def _serialize_question(q: OnboardingQuestion) -> dict:
    opts = sorted(q.options, key=lambda x: x.order_index)
    return {
        "id": q.id, "text": q.text, "qtype": q.qtype, "category": q.category,
        "order_index": q.order_index, "options": [_serialize_option(o) for o in opts],
    }


def _serialize_task(task: OnboardingTask, doc_name: str | None = None) -> dict:
    qs = sorted(task.questions, key=lambda x: x.order_index)
    return {
        "id": task.id, "plan_id": task.plan_id, "title": task.title,
        "description": task.description, "day_number": task.day_number,
        "category": task.category, "order_index": task.order_index or 0,
        "estimated_minutes": task.estimated_minutes, "document_id": task.document_id,
        "document_name": doc_name, "questions": [_serialize_question(q) for q in qs],
    }


def _doc_name(db: Session, document_id: str | None) -> str | None:
    if not document_id:
        return None
    doc = db.query(Document).filter(Document.id == document_id).first()
    return doc.name if doc else None


def _plan_out(db: Session, plan: OnboardingPlan) -> dict:
    count = db.query(OnboardingTask).filter(OnboardingTask.plan_id == plan.id).count()
    return {
        "id": plan.id, "company_id": plan.company_id, "name": plan.name,
        "description": plan.description, "target_role_id": plan.target_role_id,
        "target_department_id": plan.target_department_id, "duration_days": plan.duration_days,
        "auto_assign": plan.auto_assign or False, "is_active": plan.is_active if plan.is_active is not None else True,
        "pass_threshold": plan.pass_threshold if plan.pass_threshold is not None else 70,
        "task_count": count, "created_at": plan.created_at,
    }


# ─── VALIDACIÓN / PERSISTENCIA DE PREGUNTAS ──────────────────────────────────

def _validate_questions(category: str, questions: List[QuestionCreate]):
    if category != "cuestionario":
        return
    if not questions:
        raise HTTPException(status_code=400, detail="Un paso tipo cuestionario debe tener al menos una pregunta.")
    for i, q in enumerate(questions, 1):
        if not q.text.strip():
            raise HTTPException(status_code=400, detail=f"La pregunta {i} no tiene enunciado.")
        if len(q.options) < 2:
            raise HTTPException(status_code=400, detail=f"La pregunta {i} debe tener al menos 2 opciones.")
        correct = sum(1 for o in q.options if o.is_correct)
        if correct < 1:
            raise HTTPException(status_code=400, detail=f"La pregunta {i} debe tener al menos una opción correcta.")
        if q.qtype == "single" and correct != 1:
            raise HTTPException(status_code=400, detail=f"La pregunta {i} es de respuesta única: marca exactamente una correcta.")


def _persist_questions(db: Session, task_id: str, questions: List[QuestionCreate]):
    for qi, q in enumerate(questions):
        question = OnboardingQuestion(
            task_id=task_id, text=q.text.strip(), qtype=q.qtype,
            category=q.category, order_index=q.order_index if q.order_index else qi,
        )
        db.add(question)
        db.flush()
        for oi, opt in enumerate(q.options):
            db.add(OnboardingQuestionOption(
                question_id=question.id, text=opt.text, is_correct=opt.is_correct,
                order_index=opt.order_index if opt.order_index else oi,
            ))


def _validate_document(db: Session, document_id: str | None, company_id: str):
    if not document_id:
        return
    doc = db.query(Document).filter(
        Document.id == document_id, Document.company_id == company_id
    ).first()
    if not doc:
        raise HTTPException(status_code=400, detail="Documento inválido para tu empresa.")


def _get_company_plan(db: Session, plan_id: str, company_id: str) -> OnboardingPlan:
    plan = db.query(OnboardingPlan).filter(
        OnboardingPlan.id == plan_id, OnboardingPlan.company_id == company_id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return plan


# ─── PLANES (CRUD) ───────────────────────────────────────────────────────────

@router.get("/", response_model=List[OnboardingPlanOut])
def get_plans(db: Session = Depends(get_db), current_user: User = Depends(require_rrhh)):
    plans = db.query(OnboardingPlan).filter(
        OnboardingPlan.company_id == current_user.company_id
    ).order_by(OnboardingPlan.created_at.desc()).all()
    return [_plan_out(db, p) for p in plans]


@router.post("/", response_model=OnboardingPlanOut)
def create_plan(
    data: OnboardingPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="El nombre del plan es obligatorio.")
    plan = OnboardingPlan(
        company_id=current_user.company_id,
        name=data.name.strip(),
        description=data.description,
        target_role_id=data.target_role_id,
        target_department_id=data.target_department_id,
        duration_days=data.duration_days,
        auto_assign=data.auto_assign,
        pass_threshold=max(0, min(100, data.pass_threshold)),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_out(db, plan)


@router.patch("/{plan_id}", response_model=OnboardingPlanOut)
def update_plan(
    plan_id: str,
    data: OnboardingPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    plan = _get_company_plan(db, plan_id, current_user.company_id)
    updates = data.model_dump(exclude_unset=True)
    if "pass_threshold" in updates and updates["pass_threshold"] is not None:
        updates["pass_threshold"] = max(0, min(100, updates["pass_threshold"]))
    for field, value in updates.items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return _plan_out(db, plan)


@router.delete("/{plan_id}")
def delete_plan(plan_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_rrhh)):
    plan = _get_company_plan(db, plan_id, current_user.company_id)
    assigned = db.query(EmployeePlan).filter(EmployeePlan.plan_id == plan_id).count()
    if assigned > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: el plan está asignado a {assigned} empleado(s). Desactívalo en su lugar.",
        )
    db.delete(plan)
    db.commit()
    return {"mensaje": "Plan eliminado"}


@router.get("/{plan_id}/tasks", response_model=List[OnboardingTaskOut])
def get_plan_tasks(plan_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_rrhh)):
    _get_company_plan(db, plan_id, current_user.company_id)
    tasks = db.query(OnboardingTask).filter(
        OnboardingTask.plan_id == plan_id
    ).order_by(OnboardingTask.order_index, OnboardingTask.day_number).all()
    return [_serialize_task(t, _doc_name(db, t.document_id)) for t in tasks]


# ─── PASOS DEL PLAN (CRUD) ───────────────────────────────────────────────────

@router.post("/{plan_id}/tasks", response_model=OnboardingTaskOut)
def create_task(
    plan_id: str,
    data: OnboardingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    _get_company_plan(db, plan_id, current_user.company_id)
    _validate_questions(data.category, data.questions)
    _validate_document(db, data.document_id, current_user.company_id)

    # order_index por defecto = al final
    order = data.order_index
    if not order:
        last = db.query(OnboardingTask).filter(OnboardingTask.plan_id == plan_id).count()
        order = last

    task = OnboardingTask(
        plan_id=plan_id,
        title=data.title.strip(),
        description=data.description,
        day_number=data.day_number,
        category=data.category,
        order_index=order,
        estimated_minutes=data.estimated_minutes,
        document_id=data.document_id if data.category == "documento" else None,
    )
    db.add(task)
    db.flush()
    if data.category == "cuestionario":
        _persist_questions(db, task.id, data.questions)
    db.commit()
    db.refresh(task)
    return _serialize_task(task, _doc_name(db, task.document_id))


@router.patch("/tasks/{task_id}", response_model=OnboardingTaskOut)
def update_task(
    task_id: str,
    data: OnboardingTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    task = (
        db.query(OnboardingTask)
        .join(OnboardingPlan, OnboardingTask.plan_id == OnboardingPlan.id)
        .filter(OnboardingTask.id == task_id, OnboardingPlan.company_id == current_user.company_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Paso no encontrado")

    updates = data.model_dump(exclude_unset=True)
    new_questions = updates.pop("questions", None)
    new_category = updates.get("category", task.category)

    if "document_id" in updates:
        _validate_document(db, updates["document_id"], current_user.company_id)

    for field, value in updates.items():
        setattr(task, field, value)
    # Si deja de ser documento, se limpia el enlace
    if task.category != "documento":
        task.document_id = None

    # Si se envían preguntas (o cambia a cuestionario), se reemplazan
    if new_questions is not None or new_category == "cuestionario":
        qs = [QuestionCreate(**q) if isinstance(q, dict) else q for q in (new_questions or [])]
        if new_category == "cuestionario":
            _validate_questions("cuestionario", qs)
        db.query(OnboardingQuestion).filter(OnboardingQuestion.task_id == task.id).delete()
        db.flush()
        if new_category == "cuestionario":
            _persist_questions(db, task.id, qs)

    db.commit()
    db.refresh(task)
    return _serialize_task(task, _doc_name(db, task.document_id))


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_rrhh)):
    task = (
        db.query(OnboardingTask)
        .join(OnboardingPlan, OnboardingTask.plan_id == OnboardingPlan.id)
        .filter(OnboardingTask.id == task_id, OnboardingPlan.company_id == current_user.company_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Paso no encontrado")
    db.delete(task)
    db.commit()
    return {"mensaje": "Paso eliminado"}


# ─── ASIGNACIÓN ──────────────────────────────────────────────────────────────

@router.post("/{plan_id}/assign", response_model=EmployeePlanOut)
def assign_plan(
    plan_id: str,
    data: AssignPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    plan = _get_company_plan(db, plan_id, current_user.company_id)
    user = db.query(User).filter(
        User.id == data.user_id, User.company_id == current_user.company_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if has_active_assignment(db, user.id, plan.id):
        raise HTTPException(status_code=400, detail="El empleado ya tiene este plan asignado.")

    ep = assign_plan_to_user(db, plan, user)
    db.commit()
    db.refresh(ep)
    return ep


@router.get("/assignments/user/{user_id}", response_model=List[EmployeePlanOut])
def get_user_assignments(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    user = db.query(User).filter(
        User.id == user_id, User.company_id == current_user.company_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return db.query(EmployeePlan).filter(
        EmployeePlan.user_id == user_id
    ).order_by(EmployeePlan.assigned_at.desc()).all()
