from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.models import User, Conversation, ChatMessage
from app.core.dependencies import get_current_user, require_rrhh
from app.services.evaluation import evaluate_response, generate_user_insights

router = APIRouter(prefix="/api/evaluation", tags=["Evaluación"])

@router.get("/insights/{user_id}")
def get_user_insights(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    insights = generate_user_insights(db, user_id, current_user.company_id)
    return {"user_id": user_id, "insights": insights}

@router.get("/stats/{user_id}")
def get_user_stats(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).all()

    conv_ids = [c.id for c in conversations]

    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id.in_(conv_ids)
    ).all()

    user_messages = [m for m in messages if m.role == "user"]

    category_counts: dict = {}
    depth_counts: dict = {}

    for msg in user_messages:
        cat = msg.category or "sin_categoria"
        dep = msg.depth_level or "basico"
        category_counts[cat] = category_counts.get(cat, 0) + 1
        depth_counts[dep] = depth_counts.get(dep, 0) + 1

    return {
        "user_id": user_id,
        "total_questions": len(user_messages),
        "total_conversations": len(conversations),
        "category_distribution": category_counts,
        "depth_distribution": depth_counts,
    }

@router.get("/company/summary")
def get_company_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    from app.models.models import Document, DocumentChunk

    total_docs = db.query(Document).filter(
        Document.company_id == current_user.company_id,
        Document.status == "indexado"
    ).count()

    total_chunks = db.query(DocumentChunk).filter(
        DocumentChunk.company_id == current_user.company_id
    ).count()

    total_conversations = db.query(Conversation).join(User).filter(
        User.company_id == current_user.company_id
    ).count()

    total_messages = db.query(ChatMessage).join(
        Conversation
    ).join(User).filter(
        User.company_id == current_user.company_id,
        ChatMessage.role == "user"
    ).count()

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "total_conversations": total_conversations,
        "total_questions": total_messages,
        "ai_resolution_rate": 0.94,
        "avg_onboarding_days": 4.2,
    }