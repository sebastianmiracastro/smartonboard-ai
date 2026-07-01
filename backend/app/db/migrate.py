"""Migraciones ligeras para PostgreSQL.

create_all() crea tablas nuevas pero NO agrega columnas a tablas existentes.
Esta función agrega columnas faltantes con ALTER TABLE de forma idempotente,
para no tener que borrar la base de datos en cada cambio de esquema.

Usa el inspector de SQLAlchemy para detectar tablas y columnas existentes.
"""
from sqlalchemy import text, inspect
from app.db.database import engine

# tabla -> { columna: definición SQL (sintaxis PostgreSQL) }
COLUMNS = {
    "companies": {
        "openai_api_key": "TEXT",
        "ai_model": "VARCHAR DEFAULT 'gpt-4o-mini'",
        "ai_temperature": "FLOAT DEFAULT 0.4",
        "agent_name": "VARCHAR DEFAULT 'Sara'",
        "welcome_message": "TEXT",
        "rag_top_k": "INTEGER DEFAULT 5",
        "rag_min_similarity": "FLOAT DEFAULT 0.35",
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
        "error_message": "TEXT",
        "file_data": "BYTEA",
        "file_path": "VARCHAR",
        "manual_category": "VARCHAR",
    },
    "rrhh_alerts": {
        "kind": "VARCHAR DEFAULT 'solicitud'",
    },
    "document_chunks": {
        "category": "VARCHAR",
        "topic": "VARCHAR",
        "complexity": "VARCHAR",
        "cargo_ids": "TEXT",
    },
    "onboarding_plans": {
        "auto_assign": "BOOLEAN DEFAULT false",
        "is_active": "BOOLEAN DEFAULT true",
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
        "started_at": "TIMESTAMP",
        "last_resumed_at": "TIMESTAMP",
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

# Columnas ELIMINADAS del modelo que conviene retirar de bases ya existentes.
# En bases nuevas ni se crean (el modelo ya no las define); esto solo limpia las
# antiguas de forma idempotente. tabla -> [columnas]
DROPPED_COLUMNS = {
    "users": ["onboarding_day", "onboarding_total_days"],  # el progreso se deriva de los planes
}


def run_migrations():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, cols in COLUMNS.items():
            if table not in existing_tables:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col, ddl in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))

        # Retirar columnas obsoletas si aún existen (idempotente).
        for table, cols in DROPPED_COLUMNS.items():
            if table not in existing_tables:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col in cols:
                if col in existing:
                    conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {col}"))
