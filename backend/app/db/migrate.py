"""Migraciones ligeras para SQLite en desarrollo.

create_all() crea tablas nuevas pero NO agrega columnas a tablas existentes.
Esta función agrega columnas faltantes con ALTER TABLE de forma idempotente,
para no tener que borrar la base de datos en cada cambio de esquema.
"""
from sqlalchemy import text
from app.db.database import engine

# tabla -> { columna: definición SQL }
COLUMNS = {
    "companies": {
        "openai_api_key": "TEXT",
        "ai_model": "VARCHAR DEFAULT 'gpt-4o-mini'",
        "ai_temperature": "FLOAT DEFAULT 0.4",
        "agent_name": "VARCHAR DEFAULT 'Sara'",
        "welcome_message": "TEXT",
        "rag_top_k": "INTEGER DEFAULT 5",
    },
    "payroll_periods": {
        "frequency": "VARCHAR",
        "factor": "FLOAT DEFAULT 1.0",
        "month_key": "VARCHAR",
        "kind": "VARCHAR DEFAULT 'nomina'",
        "days": "INTEGER",
    },
    "payslips": {
        "employee_document": "VARCHAR",
        "employee_role": "VARCHAR",
        "period_name": "VARCHAR",
        "period_start": "VARCHAR",
        "period_end": "VARCHAR",
        "days": "INTEGER",
        "kind": "VARCHAR",
        "monthly_salary": "FLOAT DEFAULT 0",
    },
    "chat_messages": {
        "tools_used": "TEXT",
        "matched_category": "VARCHAR",
        "answer_confidence": "FLOAT",
        "comprehension_score": "FLOAT",
    },
    "documents": {
        "primary_category": "VARCHAR",
        "target_role_ids": "TEXT",
    },
    "document_chunks": {
        "category": "VARCHAR",
        "topic": "VARCHAR",
        "complexity": "VARCHAR",
        "cargo_ids": "TEXT",
    },
    "onboarding_plans": {
        "auto_assign": "BOOLEAN DEFAULT 0",
        "is_active": "BOOLEAN DEFAULT 1",
        "pass_threshold": "INTEGER DEFAULT 70",
    },
    "onboarding_tasks": {
        "order_index": "INTEGER DEFAULT 0",
        "document_id": "VARCHAR",
    },
    "employee_tasks": {
        "employee_plan_id": "VARCHAR",
        "order_index": "INTEGER DEFAULT 0",
        "estimated_minutes": "INTEGER DEFAULT 0",
        "time_spent_seconds": "INTEGER DEFAULT 0",
        "started_at": "DATETIME",
        "last_resumed_at": "DATETIME",
        "document_id": "VARCHAR",
    },
    "users": {
        "document_id": "VARCHAR",
        "gender": "VARCHAR",
        "birth_date": "VARCHAR",
        "phone": "VARCHAR",
        "address": "VARCHAR",
        "marital_status": "VARCHAR",
        "num_children": "INTEGER DEFAULT 0",
        "contract_type": "VARCHAR",
        "base_salary": "FLOAT DEFAULT 0",
        "bank_name": "VARCHAR",
        "bank_account": "VARCHAR",
    },
}


def run_migrations():
    with engine.connect() as conn:
        for table, cols in COLUMNS.items():
            # ¿existe la tabla?
            exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                {"t": table},
            ).first()
            if not exists:
                continue
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            for col, ddl in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
        conn.commit()
