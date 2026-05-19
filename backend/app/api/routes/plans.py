from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import OnboardingPlan, OnboardingTask, User
from app.schemas.schemas import OnboardingPlanCreate, OnboardingPlanOut, OnboardingTaskCreate, OnboardingTaskOut
from app.core.dependencies import get_current_user, require_rrhh

router = APIRouter(prefix="/api/plans", tags=["Planes de onboarding"])

@router.get("/", response_model=List[OnboardingPlanOut])
def get_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    return db.query(OnboardingPlan).filter(
        OnboardingPlan.company_id == current_user.company_id
    ).all()

@router.post("/", response_model=OnboardingPlanOut)
def create_plan(
    data: OnboardingPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    plan = OnboardingPlan(
        company_id=current_user.company_id,
        name=data.name,
        description=data.description,
        target_role_id=data.target_role_id,
        target_department_id=data.target_department_id,
        duration_days=data.duration_days,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.get("/{plan_id}/tasks", response_model=List[OnboardingTaskOut])
def get_plan_tasks(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    return db.query(OnboardingTask).filter(
        OnboardingTask.plan_id == plan_id
    ).order_by(OnboardingTask.day_number).all()

@router.post("/{plan_id}/tasks", response_model=OnboardingTaskOut)
def create_task(
    plan_id: str,
    data: OnboardingTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    task = OnboardingTask(
        plan_id=plan_id,
        title=data.title,
        description=data.description,
        day_number=data.day_number,
        category=data.category,
        estimated_minutes=data.estimated_minutes,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task