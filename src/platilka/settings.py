from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения"""

    # API ключи
    groq_api_key: str

    # Настройки браузера
    browser_headless: bool = True
    browser_timeout: int = 30000  # 30 секунд
    page_load_timeout: int = 10000  # 10 секунд

    # Настройки поиска
    max_search_results: int = 10
    search_timeout: int = 120  # 2 минуты

    # Настройки бронирования
    booking_timeout: int = 300  # 5 минут

    # Настройки LLM
    llm_temperature: float = 0.1
    llm_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    llm_max_retries: int = 3

    # URL сайта
    sutochno_base_url: str = "https://www.sutochno.ru"

    # Логирование
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # FastAPI
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
settings = Settings()