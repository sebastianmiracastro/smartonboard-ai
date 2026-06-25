from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import Role, Department, User
from app.schemas.schemas import RoleOut, RoleCreate
from app.core.dependencies import get_current_user, require_rrhh

router = APIRouter(prefix="/api/roles", tags=["Roles"])


def _company_department(db: Session, department_id: str, company_id: str) -> Department:
    """Devuelve el departamento si pertenece a la empresa, o 404/400."""
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept or dept.company_id != company_id:
        raise HTTPException(status_code=400, detail="Departamento inválido para tu empresa")
    return dept


@router.get("/", response_model=List[RoleOut])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Roles de los departamentos de la empresa del usuario
    return (
        db.query(Role)
        .join(Department, Role.department_id == Department.id)
        .filter(Department.company_id == current_user.company_id)
        .all()
    )


@router.post("/", response_model=RoleOut)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="El nombre del cargo es obligatorio")
    # El departamento debe pertenecer a la empresa del usuario (multi-tenant)
    _company_department(db, data.department_id, current_user.company_id)

    role = Role(
        department_id=data.department_id,
        name=data.name.strip(),
        description=data.description,
        seniority_level=data.seniority_level,
        seniority_label=data.seniority_label,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}")
def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    role = (
        db.query(Role)
        .join(Department, Role.department_id == Department.id)
        .filter(Role.id == role_id, Department.company_id == current_user.company_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Cargo no encontrado")

    # No permitir borrar un cargo con empleados asignados (integridad)
    assigned = db.query(User).filter(User.role_id == role_id).count()
    if assigned > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {assigned} empleado(s) con este cargo.",
        )

    db.delete(role)
    db.commit()
    return {"mensaje": "Cargo eliminado"}
