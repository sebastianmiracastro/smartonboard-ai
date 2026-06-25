"""Configuración del agente IA por empresa.

Permite a RR.HH. guardar la clave de OpenAI (y otros parámetros del agente) desde
la interfaz, sin tocar el archivo .env. La clave se guarda en la empresa
(multi-tenant) y el agente la usa con prioridad sobre la del entorno.

Por seguridad la clave NUNCA se devuelve en claro: el GET solo informa si existe
y un fragmento enmascarado para que la UI muestre el estado.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Company, User
from app.schemas.schemas import AgentConfigOut, AgentConfigUpdate
from app.core.dependencies import get_current_user, require_rrhh

router = APIRouter(prefix="/api/config", tags=["Configuración"])

# Prefijo con el que la UI recibe la clave enmascarada; lo usamos para ignorar
# ese valor si la UI lo reenvía sin cambios.
_MASK_PREFIX = "sk-…"


def _mask(key: str | None) -> str | None:
    if not key:
        return None
    return f"{_MASK_PREFIX}{key[-4:]}"


def _to_out(company: Company) -> AgentConfigOut:
    return AgentConfigOut(
        agent_name=company.agent_name or "Sara",
        welcome_message=company.welcome_message,
        ai_model=company.ai_model or "gpt-4o-mini",
        ai_temperature=company.ai_temperature if company.ai_temperature is not None else 0.4,
        rag_top_k=company.rag_top_k or 5,
        has_api_key=bool(company.openai_api_key),
        api_key_preview=_mask(company.openai_api_key),
    )


def _get_company(db: Session, company_id: str) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


@router.get("/categories")
def get_categories(current_user: User = Depends(get_current_user)):
    """Taxonomía fija de categorías de conocimiento (referencia para la UI).

    Es fija por diseño: las preguntas y los documentos se clasifican con ella para
    que las métricas de comprensión sean comparables entre cargos y en el tiempo."""
    from app.services.tagging import CATEGORY_INFO
    return {"fixed": True, "categories": CATEGORY_INFO}


@router.get("/agent", response_model=AgentConfigOut)
def get_agent_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve la configuración del agente de la empresa del usuario."""
    return _to_out(_get_company(db, current_user.company_id))


@router.put("/agent", response_model=AgentConfigOut)
def update_agent_config(
    data: AgentConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh),
):
    """Actualiza la configuración del agente (solo RR.HH./gerencia)."""
    company = _get_company(db, current_user.company_id)

    if data.agent_name is not None:
        company.agent_name = data.agent_name.strip() or "Sara"
    if data.welcome_message is not None:
        company.welcome_message = data.welcome_message
    if data.ai_model is not None:
        company.ai_model = data.ai_model
    if data.ai_temperature is not None:
        company.ai_temperature = max(0.0, min(1.0, data.ai_temperature))
    if data.rag_top_k is not None:
        company.rag_top_k = max(1, min(10, data.rag_top_k))

    # Clave: None = no tocar, "" = borrar, otro valor = guardar.
    # Ignoramos el valor enmascarado por si la UI lo reenvía sin cambios.
    if data.openai_api_key is not None:
        key = data.openai_api_key.strip()
        if key == "":
            company.openai_api_key = None
        elif not key.startswith(_MASK_PREFIX):
            company.openai_api_key = key

    db.commit()
    db.refresh(company)
    return _to_out(company)
