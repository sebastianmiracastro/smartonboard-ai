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
- SQLAlchemy + PostgreSQL (en contenedor Docker)
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

Todo el sistema corre en Docker: base de datos PostgreSQL, backend y frontend
se levantan juntos con un solo comando.

### Requisitos
- Docker Desktop
- Git

### Levantar el proyecto

Desde la raíz del repositorio:

```bash
docker compose up --build          # DESARROLLO (hot-reload)
docker compose -f docker-compose.yml up --build   # PRODUCCIÓN
```

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend / Swagger | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

El seed (solo la Directora de RR.HH.) se aplica automáticamente al arrancar el backend.

### Reestablecer la base de datos

Borra todos los datos y vuelve a aplicar el seed:

```bash
docker compose exec backend python -m app.db.reset        # pide confirmación
docker compose exec backend python -m app.db.reset --yes  # sin confirmación
```

---

## Credenciales de prueba

El seed solo crea la Directora de RR.HH.; los demás usuarios se dan de alta desde la UI.

| Usuario | Email | Contraseña | Rol |
|---|---|---|---|
| Lucía Hernández | lucia.hernandez@novatech.co | demo123 | RR.HH. — Directora |

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

Docker Compose inyecta `backend/.env.docker` en el contenedor del backend:

```env
APP_NAME=SmartOnboard AI
DEBUG=False
DATABASE_URL=postgresql://smartonboard:smartonboard123@db:5432/smartonboard
SECRET_KEY=tu-secret-key-aqui
```

> La clave de OpenAI no se configura por entorno: cada empresa la guarda desde
> la UI (multi-tenant). Sin clave, el agente usa un sintetizador extractivo local.

---

## Autor

Estudiante de Ingeniería de Software  
Politécnico Grancolombiano · 2026