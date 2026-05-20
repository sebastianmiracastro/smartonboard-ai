# SmartOnboard AI

Plataforma inteligente de onboarding empresarial basada en agentes de IA, RAG y fine-tuning.

Proyecto de grado — Ingeniería de Software  
Politécnico Grancolombiano · 2026

---

## Descripción

SmartOnboard AI automatiza y personaliza el proceso de incorporación de nuevos empleados mediante inteligencia artificial. La plataforma permite a los departamentos de RR.HH. cargar documentación interna para que un agente conversacional inteligente acompañe al empleado durante su onboarding, respondiendo preguntas en lenguaje natural y sincronizando tareas con Jira.

---

## Stack tecnológico

### Frontend
- Next.js 16 + TypeScript
- Tailwind CSS 4
- Lucide React + Recharts

### Backend
- FastAPI (Python 3.12)
- SQLAlchemy + SQLite (desarrollo) / PostgreSQL (producción)
- JWT + OAuth2

### Inteligencia Artificial
- LangGraph — agentes autónomos con patrón ReAct
- sentence-transformers — generación de embeddings
- pgvector — búsqueda semántica vectorial
- RAGAS — evaluación automática del pipeline RAG
- LoRA/QLoRA — fine-tuning sobre TinyLlama

---

## Estructura del proyecto

Proyecto De Grado/
├── frontend/          # Next.js — interfaces de usuario
├── backend/           # FastAPI — API REST e IA
└── ml/                # Notebooks de fine-tuning (Google Colab)

---

## Instalación y ejecución

### Requisitos
- Node.js 20+
- Python 3.12
- Git

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Disponible en http://localhost:3000

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
python -m app.db.seed
uvicorn main:app --reload
```

Disponible en http://localhost:8000  
Documentación Swagger en http://localhost:8000/docs

---

## Credenciales de prueba

| Usuario | Email | Contraseña | Rol |
|---|---|---|---|
| Andrea Salcedo | andrea.salcedo@techcorp.co | demo123 | RR.HH. |
| Carlos Mejía | carlos.mejia@techcorp.co | demo123 | Empleado |
| Laura Torres | laura.torres@techcorp.co | demo123 | Empleado |
| Sebastián Ríos | sebastian.rios@techcorp.co | demo123 | Empleado |

---

## Vistas del sistema

### Panel RR.HH.
| Vista | Ruta |
|---|---|
| Login | `/login` |
| Dashboard | `/dashboard` |
| Empleados | `/dashboard/empleados` |
| Documentos | `/dashboard/documentos` |
| Departamentos | `/dashboard/departamentos` |
| Planes | `/dashboard/planes` |
| Configuración agente | `/dashboard/configuracion` |

### Portal empleado
| Vista | Ruta |
|---|---|
| Inicio | `/portal/inicio` |
| Chat con agente IA | `/portal/chat` |
| Mis tareas | `/portal/tareas` |
| Recursos | `/portal/recursos` |

---

## Arquitectura IA

### Pipeline RAG
1. RR.HH. sube documentos PDF/DOCX/TXT
2. El backend extrae el texto y lo divide en chunks semánticos
3. Se generan embeddings con `all-MiniLM-L6-v2`
4. Los vectores se almacenan en la base de datos
5. El empleado hace una pregunta en el chat
6. El agente busca los chunks más similares
7. El LLM genera una respuesta citando las fuentes

### Control de acceso (RBAC)
- Los documentos tienen permisos por departamento, rol y nivel de seniority
- El agente solo busca en documentos accesibles para el usuario
- Flags especiales `is_rrhh` e `is_gerencia` para acceso a información confidencial

### Fine-tuning
- Modelo base: TinyLlama-1.1B-Chat-v1.0
- Técnica: LoRA (Low-Rank Adaptation)
- Dataset: 15 conversaciones de onboarding en español
- Entrenamiento: Google Colab con GPU T4 gratuita
- Mejora documentada con métricas comparativas

---

## Variables de entorno

Crea un archivo `.env` en la carpeta `backend`:

```env
APP_NAME=SmartOnboard AI
DEBUG=True
DATABASE_URL=sqlite:///./smartonboard.db
SECRET_KEY=tu-secret-key-aqui
OPENAI_API_KEY=sk-tu-clave-aqui
```

---

## Autor

Estudiante de Ingeniería de Software  
Politécnico Grancolombiano · 2026