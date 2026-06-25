from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
from app.db.database import get_db
from app.models.models import User, Conversation, ChatMessage, RRHHAlert
from app.core.dependencies import get_current_user, require_rrhh
from app.services.evaluation import (
    evaluate_response, generate_user_insights,
    compute_knowledge_metrics, company_knowledge_map, compute_onboarding_metrics,
)

router = APIRouter(prefix="/api/evaluation", tags=["Evaluación"])

# Etiquetas legibles para las herramientas del agente
TOOL_LABELS = {
    "buscar_en_documentos": "Búsqueda en documentos",
    "consultar_mis_tareas": "Consulta de tareas",
    "completar_tarea": "Completar tarea",
    "escalar_a_rrhh": "Escalado a RR.HH.",
}

@router.get("/insights/{user_id}")
def get_user_insights(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    insights = generate_user_insights(db, user_id, current_user.company_id)
    return {"user_id": user_id, "insights": insights}

@router.get("/knowledge/{user_id}")
def get_user_knowledge(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Cobertura, comprensión por categoría y señales de pérdida de conocimiento."""
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return compute_knowledge_metrics(db, user)


@router.get("/company/knowledge-map")
def get_company_knowledge_map(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Matriz cargo × categoría con la comprensión media (heatmap para RR.HH.)."""
    return company_knowledge_map(db, current_user.company_id)


@router.get("/onboarding/{user_id}")
def get_user_onboarding(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Métricas del onboarding del empleado: avance, tiempo real vs estimado,
    notas e intentos de cuestionarios."""
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == current_user.company_id,
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return compute_onboarding_metrics(db, user)


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
    from statistics import mean
    from app.models.models import Document, DocumentChunk, EmployeePlan
    cid = current_user.company_id

    total_docs = db.query(Document).filter(
        Document.company_id == cid,
        Document.status == "indexado"
    ).count()

    total_chunks = db.query(DocumentChunk).filter(
        DocumentChunk.company_id == cid
    ).count()

    total_conversations = db.query(Conversation).join(User).filter(
        User.company_id == cid
    ).count()

    total_messages = db.query(ChatMessage).join(
        Conversation
    ).join(User).filter(
        User.company_id == cid,
        ChatMessage.role == "user"
    ).count()

    # Resolución IA = % de preguntas que NO requirieron escalar a RR.HH.
    escalated = db.query(ChatMessage).join(Conversation).join(User).filter(
        User.company_id == cid,
        ChatMessage.role == "assistant",
        ChatMessage.tools_used.like("%escalar_a_rrhh%"),
    ).count()
    ai_resolution_rate = (
        round(max(0, total_messages - escalated) / total_messages, 2)
        if total_messages else None
    )

    # Tiempo promedio de onboarding = duración (días) de los planes finalizados
    finalized = db.query(EmployeePlan).filter(
        EmployeePlan.company_id == cid,
        EmployeePlan.status == "finalizado",
        EmployeePlan.assigned_at.isnot(None),
        EmployeePlan.completed_at.isnot(None),
    ).all()
    days = [
        max(0.0, (ep.completed_at - ep.assigned_at).total_seconds() / 86400)
        for ep in finalized
    ]
    avg_onboarding_days = round(mean(days), 1) if days else None

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "total_conversations": total_conversations,
        "total_questions": total_messages,
        "ai_resolution_rate": ai_resolution_rate,
        "avg_onboarding_days": avg_onboarding_days,
    }


@router.get("/company/analytics")
def get_company_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Distribuciones agregadas (por toda la empresa) para alimentar las gráficas
    del dashboard: preguntas por categoría, por profundidad y uso de herramientas
    del agente."""
    company_id = current_user.company_id

    user_messages = db.query(ChatMessage).join(Conversation).join(User).filter(
        User.company_id == company_id,
        ChatMessage.role == "user",
    ).all()

    assistant_messages = db.query(ChatMessage).join(Conversation).join(User).filter(
        User.company_id == company_id,
        ChatMessage.role == "assistant",
    ).all()

    category_counts: dict = {}
    depth_counts: dict = {}
    for m in user_messages:
        cat = m.category or "sin_categoria"
        dep = m.depth_level or "basico"
        category_counts[cat] = category_counts.get(cat, 0) + 1
        depth_counts[dep] = depth_counts.get(dep, 0) + 1

    # Uso de herramientas del agente (leer tools_used de los mensajes del asistente)
    tool_counts: dict = {}
    for m in assistant_messages:
        if not m.tools_used:
            continue
        try:
            for t in json.loads(m.tools_used):
                tool_counts[t] = tool_counts.get(t, 0) + 1
        except (ValueError, TypeError):
            continue

    def to_series(counts: dict) -> List[dict]:
        return [{"name": k, "value": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]

    return {
        "categories": to_series(category_counts),
        "depths": to_series(depth_counts),
        "tools": [
            {"name": TOOL_LABELS.get(k, k), "key": k, "value": v}
            for k, v in sorted(tool_counts.items(), key=lambda x: -x[1])
        ],
        "total_questions": len(user_messages),
    }


@router.get("/alerts")
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    """Alertas generadas por el agente para que RR.HH. acompañe a empleados.
    Las pendientes primero, con el nombre del empleado resuelto."""
    alerts = db.query(RRHHAlert).filter(
        RRHHAlert.company_id == current_user.company_id
    ).order_by(RRHHAlert.created_at.desc()).all()

    user_ids = {a.user_id for a in alerts}
    names = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        names = {u.id: u.full_name for u in users}

    data = [
        {
            "id": a.id,
            "user_id": a.user_id,
            "user_name": names.get(a.user_id, a.user_id),
            "motivo": a.motivo,
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]
    # pendientes primero
    data.sort(key=lambda x: 0 if x["status"] == "pendiente" else 1)
    return {"alerts": data, "pending_count": sum(1 for a in data if a["status"] == "pendiente")}


@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_rrhh)
):
    alert = db.query(RRHHAlert).filter(
        RRHHAlert.id == alert_id,
        RRHHAlert.company_id == current_user.company_id,
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    alert.status = "atendida"
    db.commit()
    return {"ok": True, "status": alert.status}