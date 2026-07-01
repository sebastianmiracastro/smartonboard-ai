from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import Conversation, ChatMessage, User, Company
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

    from app.services.agent import generate_title

    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    # Historial previo (antes de guardar el mensaje actual) para dar memoria al agente
    previous = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv_id
    ).order_by(ChatMessage.created_at).all()
    history = [{"role": m.role, "content": m.content} for m in previous]
    is_first_exchange = len(history) == 0

    # Guardar mensaje del usuario
    user_msg = ChatMessage(
        conversation_id=conv_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)
    db.commit()

    # Configuración del agente de la empresa (clave de IA, modelo, etc.)
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    company_key = company.openai_api_key if company else None
    company_model = (company.ai_model if company else None) or "gpt-4o-mini"
    company_temperature = company.ai_temperature if (company and company.ai_temperature is not None) else 0.4
    company_agent_name = (company.agent_name if company else None) or "Sara"
    company_top_k = (company.rag_top_k if company else None) or 5
    company_min_sim = (company.rag_min_similarity if (company and company.rag_min_similarity is not None) else 0.35)

    # Ejecutar agente
    try:
        result = run_agent(
            question=data.content,
            company_id=current_user.company_id,
            db=db,
            user_id=current_user.id,
            user_is_rrhh=current_user.system_role == "rrhh",
            user_is_gerencia=current_user.system_role == "gerencia",
            user_seniority_level=current_user.role.seniority_level if current_user.role else 1,
            user_department_id=current_user.department_id,
            user_role_id=current_user.role_id,
            history=history,
            openai_api_key=company_key,
            ai_model=company_model,
            ai_temperature=company_temperature,
            agent_name=company_agent_name,
            rag_top_k=company_top_k,
            rag_min_similarity=company_min_sim,
        )
    except Exception as e:
        print(f"Error en el agente: {e}")
        raise HTTPException(status_code=500, detail="El agente no pudo procesar la pregunta. Inténtalo de nuevo.")

    # Clasificar también la pregunta del usuario (la categoría vive en la pregunta;
    # así las métricas que agregan mensajes de usuario quedan pobladas).
    user_msg.category = result["category"]
    user_msg.depth_level = result["depth_level"]
    db.add(user_msg)

    # Guardar respuesta del agente
    assistant_msg = ChatMessage(
        conversation_id=conv_id,
        role="assistant",
        content=result["answer"],
        sources=json.dumps(result["sources"]),
        tools_used=json.dumps(result["tools_used"]),
        category=result["category"],
        depth_level=result["depth_level"],
        matched_category=result.get("matched_category"),
        answer_confidence=result.get("answer_confidence"),
        comprehension_score=result.get("comprehension_score"),
    )
    db.add(assistant_msg)

    # Título automático en el primer intercambio (o si sigue con el título por defecto)
    if is_first_exchange or not conv.title or conv.title == "Nueva conversación":
        conv.title = generate_title(
            data.content, result["answer"],
            api_key=company_key, model=company_model,
        )
        db.add(conv)

    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg


@router.delete("/conversations/{conv_id}")
def delete_conversation(
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

    db.query(ChatMessage).filter(ChatMessage.conversation_id == conv_id).delete()
    db.delete(conv)
    db.commit()
    return {"ok": True}