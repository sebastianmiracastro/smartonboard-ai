from datetime import datetime
from typing import List, Dict, Optional, Tuple
from statistics import mean
from sqlalchemy.orm import Session
from app.models.models import (
    ChatMessage, Conversation, User, DocumentChunk, Role, Department,
    EmployeePlan, EmployeeTask, QuizAttempt, QuizAnswer,
)
from app.services.tagging import CATEGORIES
import json

# Umbrales de las métricas de conocimiento (centralizados para defenderlos en la tesis)
LOSS_THRESHOLD = 0.15          # caída de comprensión que se considera "pérdida"
LOW_COMPREHENSION = 0.45       # comprensión media por debajo de la cual hay que reforzar
MIN_MSGS_FOR_TREND = 4         # mensajes mínimos en una categoría para evaluar tendencia
MIN_MSGS_FOR_REINFORCE = 3     # preguntas mínimas para marcar una categoría como "a reforzar"

def evaluate_response(
    question: str,
    answer: str,
    context: str,
) -> Dict[str, float]:
    """
    Evaluación liviana sin necesidad de API key.
    Implementa métricas similares a RAGAS de forma local.
    """

    scores = {}

    # 1. Faithfulness — qué tan fiel es la respuesta al contexto
    if not context:
        scores["faithfulness"] = 0.0
    else:
        context_words = set(context.lower().split())
        answer_words = set(answer.lower().split())
        common = context_words.intersection(answer_words)
        scores["faithfulness"] = min(len(common) / max(len(answer_words), 1), 1.0)

    # 2. Answer relevancy — qué tan relevante es la respuesta a la pregunta
    question_words = set(question.lower().split())
    answer_words = set(answer.lower().split())
    common_qa = question_words.intersection(answer_words)
    scores["answer_relevancy"] = min(len(common_qa) / max(len(question_words), 1), 1.0)

    # 3. Context precision — si el contexto era necesario
    if context and len(answer) > 50:
        scores["context_precision"] = 0.8
    elif not context and len(answer) > 50:
        scores["context_precision"] = 0.5
    else:
        scores["context_precision"] = 0.3

    # 4. Score global
    scores["overall"] = round(
        (scores["faithfulness"] * 0.4 +
         scores["answer_relevancy"] * 0.4 +
         scores["context_precision"] * 0.2), 3
    )

    return scores

def analyze_question_category(question: str, answer: str) -> Dict:
    q = question.lower()

    # Detectar confusión — pregunta muy corta o respuesta sin fuente
    is_confused = len(question.split()) <= 3 or "no tengo información" in answer.lower()

    # Detectar si es repetición común
    common_questions = [
        "vacacion", "salario", "jira", "responsabilidad",
        "reporto", "horario", "beneficio"
    ]
    is_common = any(w in q for w in common_questions)

    return {
        "indicates_confusion": is_confused,
        "is_common_question": is_common,
        "question_length": len(question.split()),
        "answer_has_source": "fragmento" in answer.lower() or "documento" in answer.lower(),
    }

# ─── MÉTRICAS DE CONOCIMIENTO ────────────────────────────────────────────────

def _assistant_messages_for_user(db: Session, user_id: str) -> List[ChatMessage]:
    """Mensajes del asistente del usuario, ordenados por tiempo. Llevan
    `category`, `comprehension_score` y `created_at` → base de la serie temporal."""
    conv_ids = [c.id for c in db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).all()]
    if not conv_ids:
        return []
    return db.query(ChatMessage).filter(
        ChatMessage.conversation_id.in_(conv_ids),
        ChatMessage.role == "assistant",
    ).order_by(ChatMessage.created_at).all()


def _quiz_signals_for_user(db: Session, user_id: str) -> List[Tuple[str, float, object]]:
    """Señales de comprensión provenientes de los cuestionarios: cada respuesta
    con categoría aporta 1.0 si fue correcta, 0.0 si no. Devuelve (cat, score, ts)."""
    rows = (
        db.query(QuizAnswer.category, QuizAnswer.is_correct, QuizAttempt.created_at)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .filter(QuizAttempt.user_id == user_id, QuizAnswer.category.isnot(None))
        .all()
    )
    return [(cat, 1.0 if correct else 0.0, ts) for cat, correct, ts in rows]


def _comprehension_signals_for_user(db: Session, user_id: str) -> List[Tuple[str, float, object]]:
    """Stream temporal de señales de comprensión por categoría, combinando el chat
    (proxy RAG) y los cuestionarios (acierto/fallo). Ordenado por tiempo."""
    signals: List[Tuple[str, float, object]] = []
    for m in _assistant_messages_for_user(db, user_id):
        if m.comprehension_score is not None:
            signals.append((m.category or "sin_categoria", m.comprehension_score, m.created_at))
    signals.extend(_quiz_signals_for_user(db, user_id))
    signals.sort(key=lambda s: s[2] or datetime.min)
    return signals


def available_categories_for_user(db: Session, user: User) -> set:
    """Categorías que el cargo del usuario 'debería' conocer, según los documentos
    etiquetados (cargo_ids vacío = aplica a todos)."""
    rows = db.query(DocumentChunk.category, DocumentChunk.cargo_ids).filter(
        DocumentChunk.company_id == user.company_id,
        DocumentChunk.category.isnot(None),
    ).all()
    available = set()
    for cat, cargo_ids in rows:
        if not cat:
            continue
        ids = []
        if cargo_ids:
            try:
                ids = json.loads(cargo_ids)
            except (ValueError, TypeError):
                ids = []
        if not ids or (user.role_id and user.role_id in ids):
            available.add(cat)
    return available


def _trend_loss(scores_in_time: List[float]) -> float:
    """Pérdida = caída de comprensión entre la primera y la segunda mitad temporal.
    0 si no hay datos suficientes."""
    if len(scores_in_time) < MIN_MSGS_FOR_TREND:
        return 0.0
    mid = len(scores_in_time) // 2
    early = scores_in_time[:mid]
    recent = scores_in_time[mid:]
    if not early or not recent:
        return 0.0
    return round(max(0.0, mean(early) - mean(recent)), 3)


def compute_knowledge_metrics(db: Session, user: User) -> Dict:
    """Cobertura, comprensión por categoría y señales de pérdida de conocimiento
    para un usuario. Es la métrica central de re-entreno / pérdida de conocimiento."""
    available = available_categories_for_user(db, user)

    # Señales de comprensión en orden temporal: chat (proxy RAG) + cuestionarios.
    per_cat_scores: Dict[str, List[float]] = {}
    for cat, score, _ts in _comprehension_signals_for_user(db, user.id):
        per_cat_scores.setdefault(cat, []).append(score)
    scored_count = sum(len(v) for v in per_cat_scores.values())

    by_category = []
    loss_alerts = []
    retraining = []
    for cat in CATEGORIES:
        scores = per_cat_scores.get(cat, [])
        n = len(scores)
        comp = round(mean(scores), 3) if scores else None
        # _trend_loss solo devuelve >0 con datos suficientes (>= MIN_MSGS_FOR_TREND)
        loss = _trend_loss(scores)

        if n == 0:
            status = "sin_datos"
        elif loss >= LOSS_THRESHOLD:
            status = "perdida"
            loss_alerts.append({
                "category": cat,
                "loss": loss,
                "message": f"Caída de comprensión en '{cat}' ({loss:.2f}). Posible pérdida de conocimiento; conviene reforzar.",
            })
        elif n < MIN_MSGS_FOR_REINFORCE:
            # Hay alguna consulta pero todavía no bastan muestras para juzgar
            status = "parcial"
        elif comp is not None and comp < LOW_COMPREHENSION:
            status = "refuerzo"
        else:
            status = "ok"

        if status in ("refuerzo", "perdida"):
            retraining.append({"category": cat, "questions": n, "comprehension": comp})

        by_category.append({
            "category": cat,
            "questions": n,
            "comprehension": comp,
            "available_in_docs": cat in available,
            "loss": loss,
            "status": status,
        })

    # Cobertura: de las categorías que el cargo debería conocer, ¿cuántas ha tocado?
    asked = {cat for cat, s in per_cat_scores.items() if s and cat in CATEGORIES}
    covered = asked & available if available else asked
    missing = sorted(available - asked) if available else []
    ratio = round(len(covered) / len(available), 3) if available else None

    return {
        "user_id": user.id,
        "cargo": user.role_name,
        "total_questions": scored_count,
        "coverage": {
            "covered": len(covered),
            "available": len(available),
            "ratio": ratio,
            "missing_categories": missing,
        },
        "by_category": by_category,
        "knowledge_loss_alerts": loss_alerts,
        "retraining_candidates": retraining,
    }


def company_knowledge_map(db: Session, company_id: str) -> Dict:
    """Matriz cargo × categoría con la comprensión media de la empresa (heatmap RR.HH.)."""
    users = db.query(User).filter(User.company_id == company_id).all()
    conv_user = {
        c.id: c.user_id
        for c in db.query(Conversation).filter(
            Conversation.user_id.in_([u.id for u in users] or ["__none__"])
        ).all()
    }
    user_role = {u.id: u.role_id for u in users}

    roles = {
        r.id: r.name
        for r in db.query(Role).join(Department, Role.department_id == Department.id)
        .filter(Department.company_id == company_id).all()
    }

    msgs = db.query(ChatMessage).filter(
        ChatMessage.conversation_id.in_(list(conv_user.keys()) or ["__none__"]),
        ChatMessage.role == "assistant",
    ).all()

    # (role_id, category) -> [scores]. Combina chat (proxy RAG) y cuestionarios.
    agg: Dict[tuple, List[float]] = {}
    for m in msgs:
        if m.comprehension_score is None:
            continue
        uid = conv_user.get(m.conversation_id)
        role_id = user_role.get(uid)
        if not role_id:
            continue
        cat = m.category or "sin_categoria"
        if cat not in CATEGORIES:
            continue
        agg.setdefault((role_id, cat), []).append(m.comprehension_score)

    # Señales de cuestionarios (acierto=1.0 / fallo=0.0) por cargo y categoría
    user_ids = [u.id for u in users] or ["__none__"]
    quiz_rows = (
        db.query(QuizAnswer.category, QuizAnswer.is_correct, QuizAttempt.user_id)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .filter(QuizAttempt.user_id.in_(user_ids), QuizAnswer.category.isnot(None))
        .all()
    )
    for cat, correct, uid in quiz_rows:
        role_id = user_role.get(uid)
        if not role_id or cat not in CATEGORIES:
            continue
        agg.setdefault((role_id, cat), []).append(1.0 if correct else 0.0)

    cells = []
    for (role_id, cat), scores in agg.items():
        cells.append({
            "cargo": roles.get(role_id, role_id),
            "cargo_id": role_id,
            "category": cat,
            "comprehension": round(mean(scores), 3),
            "questions": len(scores),
        })

    return {
        "categories": CATEGORIES,
        "cargos": [{"id": rid, "name": name} for rid, name in roles.items()],
        "cells": cells,
    }


# ─── MÉTRICAS DE ONBOARDING / PLANES ─────────────────────────────────────────

def compute_onboarding_metrics(db: Session, user: User) -> Dict:
    """Métricas del onboarding del empleado: avance de planes, tiempo real vs
    estimado (eficiencia), nota e intentos de cuestionarios."""
    eps = db.query(EmployeePlan).filter(
        EmployeePlan.user_id == user.id
    ).order_by(EmployeePlan.assigned_at.desc()).all()

    plans = []
    total_real = total_est = 0
    quiz_scores: List[float] = []
    quiz_passes = quiz_total = 0
    failed_attempts = 0

    for ep in eps:
        steps = db.query(EmployeeTask).filter(
            EmployeeTask.employee_plan_id == ep.id
        ).order_by(EmployeeTask.order_index, EmployeeTask.day_number).all()
        est_seconds = sum((s.estimated_minutes or 0) for s in steps) * 60
        real_seconds = ep.time_spent_seconds or sum((s.time_spent_seconds or 0) for s in steps)
        completed = sum(1 for s in steps if s.status == "completada")

        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.employee_plan_id == ep.id
        ).order_by(QuizAttempt.created_at).all()
        for a in attempts:
            quiz_total += 1
            if a.passed:
                quiz_passes += 1
            quiz_scores.append(a.score)

        if ep.status == "perdido":
            failed_attempts += 1
        # Solo cuenta el tiempo de planes en curso o finalizados (no de los perdidos repetidos)
        if ep.status in ("en_progreso", "finalizado"):
            total_real += real_seconds
            total_est += est_seconds

        plans.append({
            "id": ep.id, "plan_name": ep.plan_name, "status": ep.status,
            "attempt_number": ep.attempt_number, "score": ep.score,
            "pass_threshold": ep.pass_threshold, "total_steps": len(steps),
            "completed_steps": completed, "time_spent_seconds": real_seconds,
            "estimated_seconds": est_seconds,
            "assigned_at": ep.assigned_at.isoformat() if ep.assigned_at else None,
            "completed_at": ep.completed_at.isoformat() if ep.completed_at else None,
            "quiz_attempts": [
                {
                    "score": a.score, "passed": a.passed, "attempt_number": a.attempt_number,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in attempts
            ],
        })

    efficiency = round(total_real / total_est, 2) if total_est > 0 else None

    return {
        "user_id": user.id,
        "plans": plans,
        "summary": {
            "total_plans": len(eps),
            "active_plans": sum(1 for e in eps if e.status in ("sin_empezar", "en_progreso")),
            "finalized_plans": sum(1 for e in eps if e.status == "finalizado"),
            "failed_attempts": failed_attempts,
            "total_time_seconds": total_real,
            "estimated_seconds": total_est,
            "efficiency_ratio": efficiency,   # <1 = más rápido que lo estimado
            "avg_quiz_score": round(mean(quiz_scores), 1) if quiz_scores else None,
            "quiz_pass_rate": round(quiz_passes / quiz_total, 2) if quiz_total else None,
            "total_quiz_attempts": quiz_total,
        },
    }


def generate_user_insights(
    db: Session,
    user_id: str,
    company_id: str
) -> List[Dict]:
    insights = []

    # Obtener todas las conversaciones del usuario
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).all()

    if not conversations:
        return []

    conv_ids = [c.id for c in conversations]

    # Obtener todos los mensajes
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id.in_(conv_ids),
        ChatMessage.role == "user"
    ).all()

    if not messages:
        return []

    # Analizar categorías
    category_counts: Dict[str, int] = {}
    confusion_count = 0

    for msg in messages:
        category = msg.category or "procesos"
        category_counts[category] = category_counts.get(category, 0) + 1

        analysis = analyze_question_category(msg.content, "")
        if analysis["indicates_confusion"]:
            confusion_count += 1

    # Generar insights
    total = len(messages)

    # Categoría más consultada
    if category_counts:
        top_category = max(category_counts, key=category_counts.get)
        insights.append({
            "type": "positivo",
            "category": top_category,
            "message": f"La categoría más consultada es '{top_category}' con {category_counts[top_category]} preguntas.",
        })

    # Alerta de confusión
    if confusion_count > total * 0.3:
        insights.append({
            "type": "alerta",
            "category": "general",
            "message": f"El empleado muestra señales de confusión en {confusion_count} de {total} preguntas. Se recomienda acompañamiento.",
        })

    # Categorías sin consultas
    all_categories = ["procesos", "rol", "cultura", "herramientas", "relaciones"]
    for cat in all_categories:
        if cat not in category_counts:
            insights.append({
                "type": "advertencia",
                "category": cat,
                "message": f"No hay preguntas sobre '{cat}'. Considera verificar si el empleado tiene claridad en este tema.",
            })

    return insights