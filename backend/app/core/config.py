from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SmartOnboard AI"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Base de datos
    DATABASE_URL: str = "sqlite:///./smartonboard.db"
    
    # JWT
    SECRET_KEY: str = "supersecretkey-cambiar-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()