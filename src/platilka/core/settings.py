import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Настройки приложения"""
    # Основные настройки API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Платилка - сервис рекомендации товаров"
    APP_HOST: str = "localhost"
    APP_PORT: int = 8000
    APP_RELOAD: bool = True

    # Настройки CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Настройки API-ключей для внешних сервисов
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY")

    # Настройки LLM
    LLM_MODEL_NAME: str = "meta-llama/llama-4-maverick-17b-128e-instruct"

    # Настройки Browser-Use
    BROWSER_HEADLESS: bool = True
    BROWSER_SLOW_MO: int = 0

    # Логирование
    LOG_LEVEL: str = "INFO"

    # Настройки сервиса
    MAX_SEARCH_RESULTS: int = 3
    MAX_RECOMMENDATIONS: int = 2

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
