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