from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import Conversation, ChatMessage, User
from app.schemas.schemas import ChatMessageCreate, ChatMessageOut, ConversationOut
from app.core.dependencies import get_current_user
import uuid
import json

router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.get("/conversations", response_model=List[ConversationOut])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.created_at.desc()).all()

@router.post("/conversations", response_model=ConversationOut)
def create_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = Conversation(
        user_id=current_user.id,
        title="Nueva conversación"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

@router.get("/conversations/{conv_id}/messages", response_model=List[ChatMessageOut])
def get_messages(
    conv_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv_id
    ).order_by(ChatMessage.created_at).all()

@router.post("/conversations/{conv_id}/messages", response_model=ChatMessageOut)
def send_message(
    conv_id: str,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.agent import run_agent

    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    # Guardar mensaje del usuario
    user_msg = ChatMessage(
        conversation_id=conv_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)
    db.commit()

    # Ejecutar agente
    try:
        result = run_agent(
            question=data.content,
            company_id=current_user.company_id,
            db=db,
            user_is_rrhh=current_user.system_role == "rrhh",
            user_is_gerencia=current_user.system_role == "gerencia",
            user_seniority_level=current_user.role.seniority_level if current_user.role else 1,
            user_department_id=current_user.department_id,
        )
    except Exception as e:
        print(f"Error en el agente: {e}")
        raise HTTPException(status_code=500, detail="El agente no pudo procesar la pregunta. Inténtalo de nuevo.")

    # Guardar respuesta del agente
    assistant_msg = ChatMessage(
        conversation_id=conv_id,
        role="assistant",
        content=result["answer"],
        sources=json.dumps(result["sources"]),
        category=result["category"],
        depth_level=result["depth_level"],
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg