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
    company = relationship("Company", back_populates="users")
    department = relationship("Department", back_populates="users")
    role = relationship("Role", back_populates="users")

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

class OnboardingPlan(Base):
    __tablename__ = "onboarding_plans"
    id = Column(String, primary_key=True, default=gen_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    target_role_id = Column(String, ForeignKey("roles.id"))
    target_department_id = Column(String, ForeignKey("departments.id"))
    duration_days = Column(Integer, default=15)
    created_at = Column(DateTime, server_default=func.now())
    tasks = relationship("OnboardingTask", back_populates="plan")

class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    plan_id = Column(String, ForeignKey("onboarding_plans.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    day_number = Column(Integer, default=1)
    category = Column(String, default="lectura")
    estimated_minutes = Column(Integer, default=30)
    plan = relationship("OnboardingPlan", back_populates="tasks")

class EmployeeTask(Base):
    __tablename__ = "employee_tasks"
    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    plan_task_id = Column(String, ForeignKey("onboarding_tasks.id"))
    title = Column(String, nullable=False)
    description = Column(String)
    category = Column(String)
    status = Column(String, default="pendiente")
    day_number = Column(Integer)
    due_date = Column(String)
    completed_at = Column(DateTime, nullable=True)
    jira_issue_key = Column(String, nullable=True)
    jira_status = Column(String, nullable=True)

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
    category = Column(String, nullable=True)
    depth_level = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    conversation = relationship("Conversation", back_populates="messages")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    embedding = Column(Text, nullable=True)  # JSON string del vector
    created_at = Column(DateTime, server_default=func.now())