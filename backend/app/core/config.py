from pydantic_settings import BaseSettings
from typing import Optional

INSECURE_DEFAULT_KEY = "supersecretkey-cambiar-en-produccion"

class Settings(BaseSettings):
    APP_NAME: str = "SmartOnboard AI"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Base de datos: PostgreSQL en contenedor Docker (ver docker-compose.yml).
    # El valor real se inyecta desde backend/.env.docker al levantar los contenedores.
    DATABASE_URL: str = "postgresql://smartonboard:smartonboard123@db:5432/smartonboard"

    # JWT
    SECRET_KEY: str = INSECURE_DEFAULT_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # La clave de IA NO se configura por entorno: cada empresa la guarda desde la UI
    # (multi-tenant). Sin clave activa, el agente usa el sintetizador extractivo propio.

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignora variables del .env que ya no usamos (p. ej. OPENAI_API_KEY)

settings = Settings()

if settings.SECRET_KEY == INSECURE_DEFAULT_KEY and not settings.DEBUG:
    raise RuntimeError(
        "SECRET_KEY no puede ser el valor por defecto en producción. "
        "Configura SECRET_KEY en el archivo .env con una clave aleatoria segura."
    )