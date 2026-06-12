# SmartOnboard AI — Contexto completo del proyecto

## Información académica
- **Institución:** Politécnico Grancolombiano — Facultad de Ingeniería y Ciencias Básicas
- **Programa:** Ingeniería de Software
- **Tipo:** Proyecto de grado nivel ingeniero
- **Año:** 2026
- **Título completo:** SmartOnboard AI: Plataforma inteligente de onboarding empresarial basada en agentes de IA, RAG y fine-tuning

---

## Descripción del problema
Las empresas pierden semanas incorporando empleados nuevos. Documentación dispersa, nadie para responder preguntas básicas, procesos manuales. Esto cuesta dinero y genera frustración.

SmartOnboard AI resuelve esto con una plataforma SaaS donde la empresa sube su documentación interna y el sistema genera automáticamente un agente conversacional inteligente que guía al empleado nuevo, responde preguntas, asigna tareas y reporta el progreso al área de RR.HH.

---

## Stack tecnológico completo

### Frontend
- Next.js 16.2.1 con App Router
- TypeScript
- Tailwind CSS 4 (sin tailwind.config.ts — usa @import "tailwindcss" en globals.css)
- Lucide React para iconos
- Recharts para gráficas
- Puerto: 3000

### Backend
- FastAPI (Python 3.12)
- SQLAlchemy + Alembic
- SQLite en desarrollo (migrar a PostgreSQL en producción)
- JWT con python-jose + passlib
- Celery + Redis para workers asíncronos
- Puerto: 8000

### Inteligencia Artificial
- LangGraph — agentes autónomos con patrón ReAct
- sentence-transformers (all-MiniLM-L6-v2) — embeddings gratuitos sin API key
- pgvector — búsqueda semántica vectorial
- RAGAS — evaluación automática del pipeline RAG
- LoRA/QLoRA con PEFT — fine-tuning sobre TinyLlama-1.1B
- OpenAI GPT-4o mini — LLM principal (requiere OPENAI_API_KEY en .env)

---

## Estructura del repositorio
Proyecto De Grado/
├── frontend/                          # Next.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/page.tsx         # Login con accesos rápidos demo
│   │   │   ├── dashboard/             # Panel RR.HH.
│   │   │   │   ├── layout.tsx         # Sidebar colapsable + topbar
│   │   │   │   ├── page.tsx           # Dashboard con métricas reales
│   │   │   │   ├── empleados/         # Lista con filtros y búsqueda
│   │   │   │   │   └── [id]/          # Detalle con scores de comprensión
│   │   │   │   ├── documentos/        # Upload real + polling de estado
│   │   │   │   ├── departamentos/     # RBAC — departamentos y roles
│   │   │   │   ├── planes/            # Planes de onboarding expandibles
│   │   │   │   └── configuracion/     # Config del agente IA
│   │   │   └── portal/                # Portal del empleado
│   │   │       ├── layout.tsx         # Sidebar con progreso
│   │   │       ├── inicio/            # Dashboard empleado
│   │   │       ├── chat/              # Chat con agente IA
│   │   │       ├── tareas/            # Tareas con Jira sync
│   │   │       └── recursos/          # Documentos accesibles
│   │   ├── lib/
│   │   │   ├── api.ts                 # Cliente HTTP centralizado
│   │   │   └── utils.ts               # cn() helper
│   │   └── mock/
│   │       └── data.ts                # Mock data para desarrollo
│   └── package.json
│
├── backend/                           # FastAPI
│   ├── main.py                        # Entry point — registra todas las rutas
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── auth.py                # Login + registro JWT
│   │   │   ├── users.py               # CRUD usuarios
│   │   │   ├── departments.py         # CRUD departamentos
│   │   │   ├── documents.py           # Upload + procesamiento + RBAC
│   │   │   ├── plans.py               # Planes de onboarding + tareas
│   │   │   ├── tasks.py               # Tareas del empleado
│   │   │   ├── chat.py                # Conversaciones + agente IA
│   │   │   └── evaluation.py          # Métricas RAGAS + insights
│   │   ├── core/
│   │   │   ├── config.py              # Settings con pydantic-settings
│   │   │   ├── security.py            # JWT + bcrypt
│   │   │   └── dependencies.py        # get_current_user + require_rrhh
│   │   ├── db/
│   │   │   ├── database.py            # Engine + SessionLocal + get_db
│   │   │   └── seed.py                # Datos iniciales de prueba
│   │   ├── models/
│   │   │   └── models.py              # SQLAlchemy — todas las tablas
│   │   ├── schemas/
│   │   │   └── schemas.py             # Pydantic — validación entrada/salida
│   │   └── services/
│   │       ├── embeddings.py          # sentence-transformers
│   │       ├── document_processor.py  # PDF/DOCX/TXT → chunks
│   │       ├── rag.py                 # Indexación + búsqueda semántica
│   │       ├── agent.py               # LangGraph ReAct agent
│   │       └── evaluation.py          # RAGAS liviano + insights
│   ├── requirements.txt
│   └── .env                           # Variables de entorno (no commitear)
│
└── ml/                                # Fine-tuning (Google Colab)
├── smartonboard_finetuning.ipynb  # Notebook completo
└── evaluation_results.json        # Métricas base vs fine-tuned

---

## Modelos de base de datos

companies          → empresa cliente (multi-tenant)
departments        → departamentos con flags is_rrhh, is_gerencia
roles              → cargos con seniority_level 1-4
users              → empleados con system_role (empleado/rrhh/gerencia)
documents          → archivos subidos con permisos RBAC
document_chunks    → fragmentos indexados con embeddings JSON
onboarding_plans   → plantillas de incorporación
onboarding_tasks   → tareas dentro de un plan
employee_tasks     → tareas asignadas a empleados
conversations      → sesiones de chat
chat_messages      → mensajes con category y depth_level

---

## Control de acceso RBAC

Tres niveles que se combinan:
1. **Por departamento** — documento visible solo para un área
2. **Por seniority** — min_seniority requerido
3. **Por flag especial** — require_rrhh o require_gerencia

El agente filtra los chunks ANTES de buscar — no es lógica en el LLM sino en la query SQL. Un empleado sin permisos simplemente no recibe esos chunks.

---

## Pipeline RAG completo

PDF/DOCX/TXT
↓ extract_text() — pypdf, python-docx
↓ chunk_text() — ventana 500 chars, overlap 50
↓ generate_embeddings_batch() — all-MiniLM-L6-v2
↓ index_document_chunks() — guarda en document_chunks con embedding JSON
Pregunta del empleado
↓ generate_embedding() — mismo modelo
↓ search_similar_chunks() — cosine_similarity contra todos los chunks
↓ build_context() — top 5 chunks más similares
↓ LangGraph agent — ReAct: retrieve → classify → answer
↓ Respuesta con fuentes

---

## Agente LangGraph

Tres nodos en el grafo:
1. **retrieve** — busca chunks relevantes en pgvector
2. **classify** — categoriza la pregunta y detecta profundidad
3. **answer** — genera respuesta con OpenAI o mock si no hay API key

Categorías de preguntas: procesos, rol, cultura, herramientas, relaciones
Niveles de profundidad: basico, intermedio, avanzado

---

## Credenciales de prueba

| Nombre | Email | Contraseña | Rol |
|---|---|---|---|
| Andrea Salcedo | andrea.salcedo@techcorp.co | demo123 | RR.HH. |
| Carlos Mejía | carlos.mejia@techcorp.co | demo123 | Empleado onboarding |
| Laura Torres | laura.torres@techcorp.co | demo123 | Empleado onboarding |
| Sebastián Ríos | sebastian.rios@techcorp.co | demo123 | Empleado onboarding |

---

## Variables de entorno (.env en backend/)

```env
APP_NAME=SmartOnboard AI
DEBUG=True
DATABASE_URL=sqlite:///./smartonboard.db
SECRET_KEY=supersecretkey-cambiar-en-produccion
OPENAI_API_KEY=        # Dejar vacío usa respuestas mock
```

---

## Cómo correr el proyecto

### Backend
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload
# Swagger en http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm run dev
# App en http://localhost:3000
```

### Seed de datos (primera vez)
```bash
cd backend
venv\Scripts\activate
python -m app.db.seed
```

---

## Problemas conocidos y pendientes

### Bugs a corregir
- Las fuentes del agente no se muestran en el chat del frontend (sources viene como JSON string del backend, hay que parsearlo)
- El detalle del empleado `/dashboard/empleados/[id]` usa mock data en lugar de datos reales de la API
- El portal de inicio muestra progreso calculado localmente, no desde el backend
- Manejo de errores incompleto — si el token expira no redirige al login automáticamente

### Mejoras pendientes
- Migrar SQLite a PostgreSQL con pgvector real
- Agregar interceptor de token expirado en api.ts
- Tests unitarios en el backend (pytest)
- Gráficas de métricas en el dashboard con Recharts
- Conectar OpenAI API real para respuestas inteligentes
- Integración real con Jira API
- Websockets para streaming de respuestas del agente
- Paginación en listas de empleados y documentos

### Mejoras futuras (trabajo futuro en defensa)
- Métricas de comprensión por empleado con análisis de preguntas
- Alertas automáticas a RR.HH. cuando score baja de umbral
- Fine-tuning continuo con conversaciones reales
- Integración con Google Calendar para tareas
- Módulo de notificaciones por email con SendGrid

---

## Objetivos del proyecto de grado

- **OE1:** Arquitectura backend escalable con FastAPI, PostgreSQL y pgvector
- **OE2:** Agente conversacional con LangGraph, RAG y herramientas externas
- **OE3:** Frontend completo con Next.js y sincronización bidireccional con Jira
- **OE4:** Pipeline de evaluación RAGAS + fine-tuning LoRA sobre Llama

---

## Fine-tuning

- Modelo base: TinyLlama/TinyLlama-1.1B-Chat-v1.0
- Técnica: LoRA (r=16, lora_alpha=32, target: q_proj, v_proj, k_proj, o_proj)
- Cuantización: 4-bit con BitsAndBytes
- Dataset: 15 conversaciones de onboarding en español
- Entrenamiento: 3 épocas en Google Colab GPU T4
- Resultados en ml/evaluation_results.json

---

## Notas importantes para Claude Code

- Tailwind 4 NO usa tailwind.config.ts — la configuración va en globals.css con @import "tailwindcss"
- El backend corre con SQLite por ahora — los embeddings se guardan como JSON string en la columna embedding de document_chunks, NO como vector nativo de pgvector
- El agente funciona sin OPENAI_API_KEY usando respuestas mock — no romper esa lógica
- Multi-tenant: cada empresa tiene su company_id, todos los queries deben filtrar por company_id
- El seed crea la empresa con id="comp-001" — los usuarios del seed tienen ese company_id hardcodeado
- Next.js 16 usa Turbopack por defecto — si hay problemas de compilación probar sin turbo