from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import Department, Role
from app.schemas.schemas import DepartmentCreate, DepartmentOut
from app.core.dependencies import get_current_user, require_rrhh
from app.models.models import User

router = APIRouter(prefix="/api/departments", tags=["Departamentos"])

@router.get("/", response_model=List[DepartmentOut])
def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Department).filter(
        Department.company_id == current_user.company_id
    ).all()

@router.post("/", response_model=DepartmentOut)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    dept = Department(
        company_id=current_user.company_id,
        name=data.name,
        description=data.description,
        is_rrhh=data.is_rrhh,
        is_gerencia=data.is_gerencia,
        color=data.color,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept

@router.delete("/{dept_id}")
def delete_department(
    dept_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    # Filtrar por empresa (multi-tenant): no se puede borrar el de otra empresa
    dept = db.query(Department).filter(
        Department.id == dept_id,
        Department.company_id == current_user.company_id,
    ).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    # Integridad: no borrar si tiene cargos o empleados asociados
    roles_count = db.query(Role).filter(Role.department_id == dept_id).count()
    if roles_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: el departamento tiene {roles_count} cargo(s). Elimínalos primero.",
        )
    users_count = db.query(User).filter(User.department_id == dept_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {users_count} empleado(s) en este departamento.",
        )

    db.delete(dept)
    db.commit()
    return {"mensaje": "Departamento eliminado"}