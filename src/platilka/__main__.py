import sys

import uvicorn
from loguru import logger

from settings import settings


def setup_logging():
    """Настройка логирования"""
    logger.remove()  # Удаляем стандартный обработчик

    # Консольный вывод
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # Файловый вывод (если указан)
    if settings.log_file:
        logger.add(
            settings.log_file,
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="100 MB",
            retention="30 days"
        )


def main():
    """Главная функция для запуска приложения"""
    setup_logging()

    logger.info("Запуск Platilka Hotel Booking Service")
    # logger.info(f"Настройки: {Settings.dict()}")

    # Проверяем обязательные переменные окружения
    if not settings.groq_api_key:
        logger.error("Не установлен GROQ_API_KEY")
        sys.exit(1)

    # Запускаем сервер
    uvicorn.run(
        "platilka.api:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
