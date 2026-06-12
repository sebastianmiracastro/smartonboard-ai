from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import UserOut
from app.core.dependencies import get_current_user, require_rrhh

router = APIRouter(prefix="/api/users", tags=["Usuarios"])

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