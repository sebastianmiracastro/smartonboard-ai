from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.models import ChatMessage, Conversation, User
from app.services.rag import search_similar_chunks
from app.services.agent import run_agent
import json

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