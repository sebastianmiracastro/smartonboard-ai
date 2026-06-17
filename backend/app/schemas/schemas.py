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

    class Config:
        from_attributes = True

# ─── ONBOARDING PLAN ─────────────────────────────────────────────────────────

class OnboardingPlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_role_id: Optional[str] = None
    target_department_id: Optional[str] = None
    duration_days: int = 15

class OnboardingPlanOut(BaseModel):
    id: str
    company_id: str
    name: str
    description: Optional[str]
    duration_days: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

# ─── ONBOARDING TASK ─────────────────────────────────────────────────────────

class OnboardingTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    day_number: int = 1
    category: str = "lectura"
    estimated_minutes: int = 30

class OnboardingTaskOut(BaseModel):
    id: str
    plan_id: str
    title: str
    description: Optional[str]
    day_number: int
    category: str
    estimated_minutes: int

    class Config:
        from_attributes = True

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
    category: Optional[str]
    depth_level: Optional[str]
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