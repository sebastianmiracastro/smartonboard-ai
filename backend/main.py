from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.models import models
from app.db.migrate import run_migrations
from app.api.routes import auth, users, departments, roles, documents, plans, tasks, chat, evaluation, payroll, config

models.Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(
    title="SmartOnboard AI",
    description="API para la plataforma de onboarding inteligente",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(departments.router)
app.include_router(roles.router)
app.include_router(documents.router)
app.include_router(plans.router)
app.include_router(tasks.router)
app.include_router(chat.router)
app.include_router(evaluation.router)
app.include_router(payroll.router)
app.include_router(config.router)

@app.get("/")
def root():
    return {"mensaje": "SmartOnboard AI API corriendo", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}