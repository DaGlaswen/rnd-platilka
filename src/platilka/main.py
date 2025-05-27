import sys

import uvicorn
from loguru import logger

from platilka.core.logging import setup_logging
from platilka.core.settings import settings


def main():
    """Главная функция для запуска приложения"""
    setup_logging()

    logger.info("Запуск Platilka Hotel Booking Service")

    # Проверяем обязательные переменные окружения
    if not settings.GROQ_API_KEY:
        logger.error("Не установлен GROQ_API_KEY")
        sys.exit(1)

    if not settings.SERPER_API_KEY:
        logger.error("Не установлен SERPER_API_KEY")
        sys.exit(1)

    # Запускаем сервер
    uvicorn.run(
        "platilka.api.app:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
