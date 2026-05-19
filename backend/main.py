from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.models import models
from app.api.routes import auth, users, departments, documents

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartOnboard AI",
    description="API para la plataforma de onboarding inteligente",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(departments.router)
app.include_router(documents.router)

@app.get("/")
def root():
    return {"mensaje": "SmartOnboard AI API corriendo", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}