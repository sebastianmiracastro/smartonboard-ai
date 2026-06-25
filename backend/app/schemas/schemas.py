from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ─── AUTH ────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ─── COMPANY ─────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str
    slug: str
    industry: Optional[str] = None

class CompanyOut(BaseModel):
    id: str
    name: str
    slug: str
    industry: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ─── CONFIGURACIÓN DEL AGENTE IA ─────────────────────────────────────────────

class AgentConfigOut(BaseModel):
    """Config del agente que se devuelve a la UI. La clave nunca se expone en
    claro: solo informamos si existe y un fragmento enmascarado."""
    agent_name: str
    welcome_message: Optional[str] = None
    ai_model: str
    ai_temperature: float
    rag_top_k: int
    has_api_key: bool
    api_key_preview: Optional[str] = None

class AgentConfigUpdate(BaseModel):
    agent_name: Optional[str] = None
    welcome_message: Optional[str] = None
    ai_model: Optional[str] = None
    ai_temperature: Optional[float] = None
    rag_top_k: Optional[int] = None
    # None = no tocar la clave; "" = borrarla; cualquier otro valor = guardarla
    openai_api_key: Optional[str] = None

# ─── DEPARTMENT ──────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_rrhh: bool = False
    is_gerencia: bool = False
    color: str = "#6366f1"

class DepartmentOut(BaseModel):
    id: str
    company_id: str
    name: str
    description: Optional[str]
    is_rrhh: bool
    is_gerencia: bool
    color: str

    class Config:
        from_attributes = True

# ─── ROLE ────────────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name: str
    department_id: str
    description: Optional[str] = None
    seniority_level: int = 1
    seniority_label: str = "Junior"

class RoleOut(BaseModel):
    id: str
    department_id: str
    name: str
    description: Optional[str]
    seniority_level: int
    seniority_label: str

    class Config:
        from_attributes = True

# ─── USER ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    department_id: Optional[str] = None
    role_id: Optional[str] = None
    system_role: str = "empleado"
    start_date: Optional[str] = None
    onboarding_total_days: int = 15
    # Datos de RR.HH.
    document_id: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    marital_status: Optional[str] = None
    num_children: int = 0
    contract_type: Optional[str] = None
    base_salary: float = 0
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department_id: Optional[str] = None
    role_id: Optional[str] = None
    system_role: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    onboarding_total_days: Optional[int] = None
    document_id: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    marital_status: Optional[str] = None
    num_children: Optional[int] = None
    contract_type: Optional[str] = None
    base_salary: Optional[float] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None

class UserOut(BaseModel):
    id: str
    company_id: str
    full_name: str
    email: str
    system_role: str
    status: str
    onboarding_day: int
    onboarding_total_days: int
    department_id: Optional[str]
    role_id: Optional[str]
    start_date: Optional[str]
    department_name: Optional[str] = None
    role_name: Optional[str] = None
    # Datos de RR.HH.
    document_id: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    marital_status: Optional[str] = None
    num_children: Optional[int] = 0
    contract_type: Optional[str] = None
    base_salary: Optional[float] = 0
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordChange(BaseModel):
    password: str

# ─── DOCUMENT ────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    company_id: str
    name: str
    format: Optional[str]
    size_kb: Optional[int]
    status: str
    progress: Optional[int]
    chunk_count: Optional[int]
    uploaded_at: Optional[datetime]
    require_rrhh: bool
    require_gerencia: bool
    primary_category: Optional[str] = None
    role_permission: Optional[str] = None
    dept_permission: Optional[str] = None
    min_seniority: Optional[int] = None

    class Config:
        from_attributes = True

# ─── ONBOARDING PLAN ─────────────────────────────────────────────────────────

class OnboardingPlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_role_id: Optional[str] = None
    target_department_id: Optional[str] = None
    duration_days: int = 15
    auto_assign: bool = False
    pass_threshold: int = 70

class OnboardingPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_role_id: Optional[str] = None
    target_department_id: Optional[str] = None
    duration_days: Optional[int] = None
    auto_assign: Optional[bool] = None
    is_active: Optional[bool] = None
    pass_threshold: Optional[int] = None

class OnboardingPlanOut(BaseModel):
    id: str
    company_id: str
    name: str
    description: Optional[str]
    target_role_id: Optional[str] = None
    target_department_id: Optional[str] = None
    duration_days: int
    auto_assign: bool = False
    is_active: bool = True
    pass_threshold: int = 70
    task_count: int = 0
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ─── CUESTIONARIO (preguntas y opciones de un paso) ──────────────────────────

class QuestionOptionCreate(BaseModel):
    text: str
    is_correct: bool = False
    order_index: int = 0

class QuestionOptionOut(BaseModel):
    id: str
    text: str
    is_correct: bool
    order_index: int

    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    text: str
    qtype: str = "single"            # single | multiple
    category: Optional[str] = None
    order_index: int = 0
    options: List[QuestionOptionCreate] = []

class QuestionOut(BaseModel):
    id: str
    text: str
    qtype: str
    category: Optional[str] = None
    order_index: int
    options: List[QuestionOptionOut] = []

    class Config:
        from_attributes = True

# ─── ONBOARDING TASK (paso del plan) ─────────────────────────────────────────

class OnboardingTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    day_number: int = 1
    category: str = "lectura"        # lectura | reunion | documento | cuestionario | tarea | configuracion | entregable
    order_index: int = 0
    estimated_minutes: int = 30
    document_id: Optional[str] = None
    questions: List[QuestionCreate] = []

class OnboardingTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    day_number: Optional[int] = None
    category: Optional[str] = None
    order_index: Optional[int] = None
    estimated_minutes: Optional[int] = None
    document_id: Optional[str] = None
    questions: Optional[List[QuestionCreate]] = None

class OnboardingTaskOut(BaseModel):
    id: str
    plan_id: str
    title: str
    description: Optional[str]
    day_number: int
    category: str
    order_index: int = 0
    estimated_minutes: int
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    questions: List[QuestionOut] = []

    class Config:
        from_attributes = True

# ─── ASIGNACIÓN DE PLANES ────────────────────────────────────────────────────

class AssignPlanRequest(BaseModel):
    user_id: str

class EmployeePlanOut(BaseModel):
    id: str
    user_id: str
    plan_id: str
    plan_name: Optional[str]
    status: str
    attempt_number: int
    score: Optional[float] = None
    pass_threshold: int = 70
    time_spent_seconds: int = 0
    assigned_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# ─── EJECUCIÓN DEL PLAN (portal del empleado) ────────────────────────────────

class EmployeeStepOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    category: str
    status: str
    order_index: int = 0
    day_number: Optional[int] = None
    estimated_minutes: int = 0
    time_spent_seconds: int = 0
    is_running: bool = False
    completed_at: Optional[datetime] = None
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    has_quiz: bool = False
    question_count: int = 0

class EmployeePlanDetailOut(BaseModel):
    id: str
    plan_id: str
    plan_name: Optional[str]
    description: Optional[str] = None
    status: str
    attempt_number: int
    score: Optional[float] = None
    pass_threshold: int = 70
    duration_days: Optional[int] = None
    time_spent_seconds: int = 0
    total_steps: int = 0
    completed_steps: int = 0
    assigned_at: Optional[datetime]
    completed_at: Optional[datetime]
    steps: List[EmployeeStepOut] = []

class QuizOptionPublic(BaseModel):
    id: str
    text: str

class QuizQuestionPublic(BaseModel):
    id: str
    text: str
    qtype: str
    options: List[QuizOptionPublic] = []

class QuizPublicOut(BaseModel):
    step_id: str
    title: str
    questions: List[QuizQuestionPublic] = []

class QuizAnswerIn(BaseModel):
    question_id: str
    selected_option_ids: List[str] = []

class QuizSubmit(BaseModel):
    answers: List[QuizAnswerIn] = []

class QuizResultOut(BaseModel):
    score: float
    passed: bool
    threshold: int
    correct_count: int
    total: int
    plan_status: str
    reset: bool = False
    new_plan_id: Optional[str] = None

# ─── EMPLOYEE TASK ───────────────────────────────────────────────────────────

class EmployeeTaskOut(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    category: Optional[str]
    status: str
    day_number: Optional[int]
    due_date: Optional[str]
    jira_issue_key: Optional[str]
    jira_status: Optional[str]

    class Config:
        from_attributes = True

# ─── CHAT ────────────────────────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: Optional[str]
    tools_used: Optional[str] = None
    category: Optional[str]
    depth_level: Optional[str]
    matched_category: Optional[str] = None
    answer_confidence: Optional[float] = None
    comprehension_score: Optional[float] = None
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class ConversationOut(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ─── NÓMINA ──────────────────────────────────────────────────────────────────

class PayrollConceptCreate(BaseModel):
    name: str
    type: str = "devengado"        # devengado | deduccion | aporte_patronal | provision
    calc_type: str = "fijo"        # fijo | porcentaje
    value: float = 0
    description: Optional[str] = None
    is_active: bool = True

class PayrollConceptUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    calc_type: Optional[str] = None
    value: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class PayrollConceptOut(BaseModel):
    id: str
    company_id: str
    name: str
    type: str
    calc_type: str
    value: float
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class PayrollPeriodCreate(BaseModel):
    name: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    month_key: Optional[str] = None  # YYYY-MM; si no se envía se deriva de period_start

class SettlementCreate(BaseModel):
    """Liquidación por terminación de un solo colaborador."""
    user_id: str
    name: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    month_key: Optional[str] = None

class PayslipItemOut(BaseModel):
    id: str
    concept_id: Optional[str]
    concept_name: str
    type: str
    amount: float

    class Config:
        from_attributes = True

class PayslipOut(BaseModel):
    id: str
    period_id: str
    user_id: str
    employee_name: Optional[str]
    employee_document: Optional[str] = None
    employee_role: Optional[str] = None
    period_name: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    days: Optional[int] = None
    kind: Optional[str] = None
    monthly_salary: Optional[float] = 0
    base_salary: float
    total_devengado: float
    total_deduccion: float
    total_aportes: float
    net_pay: float
    items: List[PayslipItemOut] = []

    class Config:
        from_attributes = True

class PayrollPeriodOut(BaseModel):
    id: str
    company_id: str
    name: str
    period_start: Optional[str]
    period_end: Optional[str]
    kind: Optional[str] = "nomina"
    factor: Optional[float] = 1.0
    days: Optional[int] = None
    month_key: Optional[str] = None
    status: str
    total_devengado: float
    total_deduccion: float
    total_aportes: float
    total_neto: float
    employee_count: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class PayrollPeriodDetailOut(PayrollPeriodOut):
    payslips: List[PayslipOut] = []

# ─── NOVEDADES INDIVIDUALES ──────────────────────────────────────────────────

class PayrollNoveltyCreate(BaseModel):
    user_id: str
    concept_name: str
    type: str = "devengado"   # devengado | deduccion | retiro
    amount: float = 0
    description: Optional[str] = None

class PayrollNoveltyOut(BaseModel):
    id: str
    company_id: str
    user_id: str
    employee_name: Optional[str]
    concept_name: str
    type: str
    amount: float
    description: Optional[str]
    applied: bool
    period_id: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ─── HISTORIAL DE CAMBIOS DEL EMPLEADO ───────────────────────────────────────

class UserChangeLogOut(BaseModel):
    id: str
    user_id: str
    changed_by_name: Optional[str]
    field: str
    field_label: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True