from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import EmployeeTask, User
from app.schemas.schemas import EmployeeTaskOut
from app.core.dependencies import get_current_user, require_rrhh

router = APIRouter(prefix="/api/tasks", tags=["Tareas del empleado"])

@router.get("/my", response_model=List[EmployeeTaskOut])
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(EmployeeTask).filter(
        EmployeeTask.user_id == current_user.id
    ).order_by(EmployeeTask.day_number).all()

@router.patch("/{task_id}/complete")
def complete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(EmployeeTask).filter(
        EmployeeTask.id == task_id,
        EmployeeTask.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    task.status = "completada"
    db.commit()
    return {"mensaje": "Tarea completada"}

VALID_STATUSES = {"pendiente", "en_progreso", "completada", "bloqueada"}

@router.patch("/{task_id}/status")
def update_task_status(
    task_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Valores permitidos: {', '.join(sorted(VALID_STATUSES))}"
        )
    task = db.query(EmployeeTask).filter(
        EmployeeTask.id == task_id,
        EmployeeTask.user_id == current_user.id
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
    current_user: User = Depends(require_rrhh)
):
    target = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return db.query(EmployeeTask).filter(
        EmployeeTask.user_id == user_id
    ).order_by(EmployeeTask.day_number).all()