from sqlalchemy import Column, String, Boolean, Integer, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

def gen_uuid():
    return str(uuid.uuid4())

class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    industry = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    # Configuración del agente IA (por empresa — multi-tenant)
    openai_api_key = Column(Text, nullable=True)        # clave introducida desde la UI; tiene prioridad sobre la del .env
    ai_model = Column(String, default="gpt-4o-mini")
    ai_temperature = Column(Float, default=0.4)
    agent_name = Column(String, default="Sara")
    welcome_message = Column(Text, nullable=True)
    rag_top_k = Column(Integer, default=5)
    rag_min_similarity = Column(Float, default=0.35)    # umbral de relevancia del RAG/extractivo (precisión ↔ cobertura)

    departments = relationship("Department", back_populates="company")
    users = relationship("User", back_populates="company")

class Department(Base):
    __tablename__ = "departments"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    is_rrhh = Column(Boolean, default=False)
    is_gerencia = Column(Boolean, default=False)
    color = Column(String, default="#6366f1")
    company = relationship("Company", back_populates="departments")
    roles = relationship("Role", back_populates="department")
    users = relationship("User", back_populates="department")

class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True, default=gen_uuid)
    department_id = Column(String, ForeignKey("departments.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    seniority_level = Column(Integer, default=1)
    seniority_label = Column(String, default="Junior")
    department = relationship("Department", back_populates="roles")
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id"))
    role_id = Column(String, ForeignKey("roles.id"))
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    system_role = Column(String, default="empleado")
    status = Column(String, default="onboarding")
    start_date = Column(String)
    onboarding_day = Column(Integer, default=1)
    onboarding_total_days = Column(Integer, default=15)
    onboarding_plan_id = Column(String, ForeignKey("onboarding_plans.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Datos de RR.HH. (información del expediente del empleado)
    document_id = Column(String, nullable=True)        # cédula / documento
    gender = Column(String, nullable=True)             # masculino / femenino / otro
    birth_date = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)     # soltero / casado / union_libre / divorciado / viudo
    num_children = Column(Integer, default=0)
    contract_type = Column(String, nullable=True)      # indefinido / fijo / obra_labor / prestacion_servicios
    base_salary = Column(Float, default=0)             # salario mensual
    bank_name = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)
    company = relationship("Company", back_populates="users")
    department = relationship("Department", back_populates="users")
    role = relationship("Role", back_populates="users")

    @property
    def department_name(self) -> str | None:
        return self.department.name if self.department else None

    @property
    def role_name(self) -> str | None:
        return self.role.name if self.role else None

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    format = Column(String)
    size_kb = Column(Integer)
    status = Column(String, default="en_cola")
    progress = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    uploaded_by = Column(String, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, server_default=func.now())
    dept_permission = Column(String, nullable=True)
    role_permission = Column(String, nullable=True)
    require_rrhh = Column(Boolean, default=False)
    require_gerencia = Column(Boolean, default=False)
    min_seniority = Column(Integer, nullable=True)
    # Categorización temática (para métricas de conocimiento, NO control de acceso)
    primary_category = Column(String, nullable=True)       # categoría dominante del documento
    target_role_ids = Column(Text, nullable=True)          # JSON: cargos a los que aplica el contenido ([] = todos)

class OnboardingPlan(Base):
    __tablename__ = "onboarding_plans"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    target_role_id = Column(String, ForeignKey("roles.id"))
    target_department_id = Column(String, ForeignKey("departments.id"))
    duration_days = Column(Integer, default=15)
    auto_assign = Column(Boolean, default=False)      # se asigna solo según el cargo objetivo
    is_active = Column(Boolean, default=True)
    pass_threshold = Column(Integer, default=70)      # nota mínima (0-100) para aprobar cuestionarios
    created_at = Column(DateTime, server_default=func.now())
    tasks = relationship("OnboardingTask", back_populates="plan", cascade="all, delete-orphan")

class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    plan_id = Column(String, ForeignKey("onboarding_plans.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    day_number = Column(Integer, default=1)
    # Tipo del paso: lectura | reunion | documento | cuestionario | tarea | configuracion | entregable
    category = Column(String, default="lectura")
    order_index = Column(Integer, default=0)
    estimated_minutes = Column(Integer, default=30)   # tiempo promedio digitado por RR.HH.
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)  # para pasos tipo documento
    plan = relationship("OnboardingPlan", back_populates="tasks")
    questions = relationship("OnboardingQuestion", back_populates="task", cascade="all, delete-orphan")

class OnboardingQuestion(Base):
    """Pregunta cerrada de un paso tipo cuestionario."""
    __tablename__ = "onboarding_questions"
    id = Column(String, primary_key=True, default=gen_uuid)
    task_id = Column(String, ForeignKey("onboarding_tasks.id"), nullable=False)
    text = Column(Text, nullable=False)
    qtype = Column(String, default="single")          # single (1 correcta) | multiple
    category = Column(String, nullable=True)          # categoría de conocimiento (opcional, para la métrica)
    order_index = Column(Integer, default=0)
    task = relationship("OnboardingTask", back_populates="questions")
    options = relationship("OnboardingQuestionOption", back_populates="question", cascade="all, delete-orphan")

class OnboardingQuestionOption(Base):
    __tablename__ = "onboarding_question_options"
    id = Column(String, primary_key=True, default=gen_uuid)
    question_id = Column(String, ForeignKey("onboarding_questions.id"), nullable=False)
    text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    question = relationship("OnboardingQuestion", back_populates="options")

class EmployeePlan(Base):
    """Instancia de un plan asignada a un empleado (un intento).

    Permite historial: cada reintento (p.ej. tras fallar un cuestionario) es una
    fila nueva; las anteriores quedan como 'perdido'."""
    __tablename__ = "employee_plans"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    plan_id = Column(String, ForeignKey("onboarding_plans.id"), nullable=False)
    plan_name = Column(String)                         # snapshot del nombre del plan
    status = Column(String, default="sin_empezar")     # sin_empezar | en_progreso | finalizado | perdido
    attempt_number = Column(Integer, default=1)
    score = Column(Float, nullable=True)               # nota global del plan (si tuvo cuestionarios)
    pass_threshold = Column(Integer, default=70)       # snapshot del umbral del plan
    time_spent_seconds = Column(Integer, default=0)
    assigned_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class EmployeeTask(Base):
    __tablename__ = "employee_tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    employee_plan_id = Column(String, ForeignKey("employee_plans.id"), nullable=True)
    plan_task_id = Column(String, ForeignKey("onboarding_tasks.id"))
    title = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)                          # tipo del paso (igual que OnboardingTask.category)
    status = Column(String, default="pendiente")       # pendiente | en_progreso | completada
    day_number = Column(Integer)
    order_index = Column(Integer, default=0)
    estimated_minutes = Column(Integer, default=0)     # snapshot del tiempo estimado
    time_spent_seconds = Column(Integer, default=0)    # tiempo real acumulado
    started_at = Column(DateTime, nullable=True)
    last_resumed_at = Column(DateTime, nullable=True)  # marca de cuándo arrancó el cronómetro
    due_date = Column(String)
    completed_at = Column(DateTime, nullable=True)
    jira_issue_key = Column(String, nullable=True)
    jira_status = Column(String, nullable=True)
    document_id = Column(String, nullable=True)        # snapshot del documento enlazado

class QuizAttempt(Base):
    """Intento de un cuestionario (paso) por un empleado. Guarda nota y aprobación."""
    __tablename__ = "quiz_attempts"
    id = Column(String, primary_key=True, default=gen_uuid)
    employee_plan_id = Column(String, ForeignKey("employee_plans.id"), nullable=False)
    employee_task_id = Column(String, ForeignKey("employee_tasks.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    score = Column(Float, default=0)                   # 0-100
    passed = Column(Boolean, default=False)
    attempt_number = Column(Integer, default=1)
    time_spent_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    answers = relationship("QuizAnswer", back_populates="attempt", cascade="all, delete-orphan")

class QuizAnswer(Base):
    """Respuesta del empleado a una pregunta dentro de un intento (historial completo)."""
    __tablename__ = "quiz_answers"
    id = Column(String, primary_key=True, default=gen_uuid)
    attempt_id = Column(String, ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(String, nullable=True)        # id de la pregunta plantilla
    question_text = Column(Text, nullable=True)        # snapshot
    category = Column(String, nullable=True)           # categoría de conocimiento de la pregunta
    selected_option_ids = Column(Text, nullable=True)  # JSON con los ids elegidos
    is_correct = Column(Boolean, default=False)
    attempt = relationship("QuizAttempt", back_populates="answers")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    messages = relationship("ChatMessage", back_populates="conversation")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(String, primary_key=True, default=gen_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)
    tools_used = Column(Text, nullable=True)  # JSON string con los nombres de herramientas usadas
    category = Column(String, nullable=True)         # categoría inferida de la PREGUNTA
    depth_level = Column(String, nullable=True)
    # Métricas de conocimiento (persistidas por intercambio para la serie temporal)
    matched_category = Column(String, nullable=True)     # categoría REAL de los chunks recuperados
    answer_confidence = Column(Float, nullable=True)     # mejor similitud del RAG (0..1)
    comprehension_score = Column(Float, nullable=True)   # qué tan resuelto quedó el intercambio (0..1)
    created_at = Column(DateTime, server_default=func.now())
    conversation = relationship("Conversation", back_populates="messages")

class PayrollConcept(Base):
    """Concepto de nómina definido por RR.HH. (genérico, sin valores legales precargados)."""
    __tablename__ = "payroll_concepts"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    # devengado | deduccion | aporte_patronal | provision
    type = Column(String, nullable=False, default="devengado")
    # fijo | porcentaje
    calc_type = Column(String, nullable=False, default="fijo")
    value = Column(Float, default=0)  # monto fijo o % según calc_type
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class PayrollPeriod(Base):
    """Período de nómina (ej. Junio 2026)."""
    __tablename__ = "payroll_periods"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    period_start = Column(String, nullable=True)
    period_end = Column(String, nullable=True)
    kind = Column(String, default="nomina")         # nomina | terminacion
    frequency = Column(String, nullable=True)       # (obsoleto) se conserva por compatibilidad
    factor = Column(Float, default=1.0)             # proporción según los días liquidados (mes = 30 días)
    days = Column(Integer, nullable=True)           # días liquidados
    month_key = Column(String, nullable=True)       # YYYY-MM para agrupar por mes
    status = Column(String, default="procesada")  # borrador | procesada | pagada
    total_devengado = Column(Float, default=0)
    total_deduccion = Column(Float, default=0)
    total_aportes = Column(Float, default=0)
    total_neto = Column(Float, default=0)
    employee_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    payslips = relationship("Payslip", back_populates="period", cascade="all, delete-orphan")

class Payslip(Base):
    """Comprobante de pago individual de un empleado en un período.

    Guarda un snapshot autocontenido (nombre/fechas/días del período y datos del
    empleado) para que el comprobante sea un documento histórico independiente.
    """
    __tablename__ = "payslips"
    id = Column(String, primary_key=True, default=gen_uuid)
    period_id = Column(String, ForeignKey("payroll_periods.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    employee_name = Column(String)
    employee_document = Column(String, nullable=True)
    employee_role = Column(String, nullable=True)
    # Snapshot del período (para que el comprobante no dependa del período)
    period_name = Column(String, nullable=True)
    period_start = Column(String, nullable=True)
    period_end = Column(String, nullable=True)
    days = Column(Integer, nullable=True)
    kind = Column(String, nullable=True)            # nomina | terminacion
    monthly_salary = Column(Float, default=0)       # salario mensual de referencia
    base_salary = Column(Float, default=0)          # salario liquidado en el período
    total_devengado = Column(Float, default=0)
    total_deduccion = Column(Float, default=0)
    total_aportes = Column(Float, default=0)
    net_pay = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())
    period = relationship("PayrollPeriod", back_populates="payslips")
    items = relationship("PayslipItem", back_populates="payslip", cascade="all, delete-orphan")

class PayslipItem(Base):
    """Línea de un comprobante: un concepto aplicado con su monto calculado."""
    __tablename__ = "payslip_items"
    id = Column(String, primary_key=True, default=gen_uuid)
    payslip_id = Column(String, ForeignKey("payslips.id"), nullable=False)
    concept_id = Column(String, nullable=True)
    concept_name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # devengado | deduccion | aporte_patronal | provision
    amount = Column(Float, default=0)
    payslip = relationship("Payslip", back_populates="items")

class PayrollNovelty(Base):
    """Novedad individual de un colaborador (bonificación extra, retiro, descuento, etc.)
    que se aplica en la próxima liquidación de nómina."""
    __tablename__ = "payroll_novelties"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    employee_name = Column(String)
    concept_name = Column(String, nullable=False)
    # devengado | deduccion | retiro
    type = Column(String, nullable=False, default="devengado")
    amount = Column(Float, default=0)
    description = Column(String, nullable=True)
    applied = Column(Boolean, default=False)
    period_id = Column(String, nullable=True)       # período donde se aplicó
    created_at = Column(DateTime, server_default=func.now())

class UserChangeLog(Base):
    """Historial de modificaciones del expediente de un empleado (auditoría)."""
    __tablename__ = "user_change_logs"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    changed_by_id = Column(String, nullable=True)
    changed_by_name = Column(String, nullable=True)
    field = Column(String, nullable=False)
    field_label = Column(String, nullable=True)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class RRHHAlert(Base):
    """Alerta generada por el agente para que RR.HH. acompañe a un empleado."""
    __tablename__ = "rrhh_alerts"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    motivo = Column(Text, nullable=False)
    status = Column(String, default="pendiente")  # pendiente | atendida
    created_at = Column(DateTime, server_default=func.now())

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    embedding = Column(Text, nullable=True)  # JSON string del vector
    # Categorización temática del fragmento (para clasificar preguntas y medir conocimiento)
    category = Column(String, nullable=True)         # una de las 5 categorías fijas
    topic = Column(String, nullable=True)            # tema fino extraído del contenido
    complexity = Column(String, nullable=True)       # basico | intermedio | avanzado
    cargo_ids = Column(Text, nullable=True)          # JSON: cargos relevantes ([] = todos)
    created_at = Column(DateTime, server_default=func.now())