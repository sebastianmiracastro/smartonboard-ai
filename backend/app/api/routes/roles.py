from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import Role, Department, User
from app.schemas.schemas import RoleOut
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/api/roles", tags=["Roles"])

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
