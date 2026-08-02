from typing import Optional
from pydantic_settings import  BaseSettings, SettingsConfigDict

model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore"
)


class Settings(BaseSettings):
    app_name: str = "Quick Paper AI"

    # Security
    SECRET_KEY: str = None
    ALGORITHM : str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES : int = 60 * 24 * 7

    #Database
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_URL : str = ""
    SUPABASE_SERVICE_ROLE_KEY : str = ""
    DB_URI : str = ""


    #LLM
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY : Optional[str] = None
    OPENROUTER_API_KEY : Optional[str] = None

    #Redis
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None
    REDIS_URL : str = ""
    # --- Email SMTP (FastMail) ---
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    FIREBASE_CREDENTIALS : str = ""


    FRONTEND_URL: str = "http://localhost:8080"



settings = Settings()