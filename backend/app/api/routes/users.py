from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import User, Role, Department, UserChangeLog
from app.schemas.schemas import UserOut, UserCreate, UserUpdate, UserChangeLogOut, PasswordChange
from app.core.security import hash_password
from app.core.dependencies import get_current_user, require_rrhh
from app.services.onboarding import auto_assign_plans_for_user, pause_running_steps

router = APIRouter(prefix="/api/users", tags=["Usuarios"])

# Etiquetas legibles de los campos auditables
FIELD_LABELS = {
    "full_name": "Nombre completo",
    "department_id": "Departamento",
    "role_id": "Cargo / Rol",
    "system_role": "Rol del sistema",
    "status": "Estado",
    "start_date": "Fecha de ingreso",
    "onboarding_total_days": "Días de onboarding",
    "document_id": "Cédula / Documento",
    "gender": "Género",
    "birth_date": "Fecha de nacimiento",
    "phone": "Teléfono",
    "address": "Dirección",
    "marital_status": "Estado civil",
    "num_children": "N° de hijos",
    "contract_type": "Tipo de contrato",
    "base_salary": "Salario base",
    "bank_name": "Banco",
    "bank_account": "N° de cuenta",
}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/", response_model=List[UserOut])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    return db.query(User).filter(
        User.company_id == current_user.company_id
    ).all()

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo ya está registrado"
        )

    # Validar que el departamento (si se envía) pertenezca a la empresa
    if data.department_id:
        dept = db.query(Department).filter(
            Department.id == data.department_id,
            Department.company_id == current_user.company_id
        ).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Departamento inválido")

    # Validar que el rol (si se envía) pertenezca a ese departamento
    if data.role_id:
        role = db.query(Role).filter(Role.id == data.role_id).first()
        if not role or (data.department_id and role.department_id != data.department_id):
            raise HTTPException(status_code=400, detail="Rol inválido para el departamento")

    user = User(
        company_id=current_user.company_id,
        full_name=data.full_name,
        email=data.email,
        hashed_password=hash_password(data.password),
        department_id=data.department_id,
        role_id=data.role_id,
        system_role=data.system_role,
        status="onboarding" if data.system_role == "empleado" else "activo",
        start_date=data.start_date,
        onboarding_total_days=data.onboarding_total_days,
        document_id=data.document_id,
        gender=data.gender,
        birth_date=data.birth_date,
        phone=data.phone,
        address=data.address,
        marital_status=data.marital_status,
        num_children=data.num_children,
        contract_type=data.contract_type,
        base_salary=data.base_salary,
        bank_name=data.bank_name,
        bank_account=data.bank_account,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Asignar automáticamente los planes del cargo (si los hay)
    auto_assign_plans_for_user(db, user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    updates = data.model_dump(exclude_unset=True)
    role_changed = False
    for field, value in updates.items():
        old = getattr(user, field, None)
        if old == value:
            continue  # sin cambio real
        if field == "role_id":
            role_changed = True
        # Registrar en el historial de auditoría
        db.add(UserChangeLog(
            user_id=user.id,
            changed_by_id=current_user.id,
            changed_by_name=current_user.full_name,
            field=field,
            field_label=FIELD_LABELS.get(field, field),
            old_value=None if old is None else str(old),
            new_value=None if value is None else str(value),
        ))
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    # Si cambió el cargo, asignar los planes automáticos del nuevo rol
    if role_changed:
        auto_assign_plans_for_user(db, user)
        db.commit()
        db.refresh(user)

    # Si el empleado queda inactivo, se pausa el cronómetro de sus pasos en curso
    if updates.get("status") == "inactivo":
        pause_running_steps(db, user)
        db.commit()
    return user

@router.patch("/{user_id}/password")
def change_user_password(
    user_id: str,
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """RR.HH./gerencia restablece la contraseña de un empleado de su empresa."""
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    pwd = (data.password or "").strip()
    if len(pwd) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    user.hashed_password = hash_password(pwd)
    # Auditoría (sin guardar la contraseña en claro)
    db.add(UserChangeLog(
        user_id=user.id,
        changed_by_id=current_user.id,
        changed_by_name=current_user.full_name,
        field="password",
        field_label="Contraseña",
        old_value=None,
        new_value="(restablecida)",
    ))
    db.commit()
    return {"mensaje": "Contraseña actualizada"}

@router.get("/{user_id}/history", response_model=List[UserChangeLogOut])
def user_history(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db.query(UserChangeLog).filter(
        UserChangeLog.user_id == user_id
    ).order_by(UserChangeLog.created_at.desc()).all()