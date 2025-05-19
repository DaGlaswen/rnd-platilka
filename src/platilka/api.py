from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from loguru import logger
import uuid
import asyncio

from .models import (
    BookingRequest, HotelInfo, HotelRecommendations,
    BookingResult, SearchStatus, ErrorResponse,
    BookingConfirmation, GuestInfo, PaymentInfo
)
from .sutochno_service import SutochnoService
from .settings import settings

# Создаем экземпляр FastAPI
app = FastAPI(
    title="Platilka Hotel Booking Service",
    description="Сервис автоматического бронирования отелей на sutochno.ru",
    version="0.1.0"
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище состояний поиска и бронирования
search_tasks: Dict[str, Dict[str, Any]] = {}
booking_confirmations: Dict[str, BookingConfirmation] = {}


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    logger.info("Запуск Platilka Hotel Booking Service API")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке приложения"""
    logger.info("Остановка Platilka Hotel Booking Service API")


# Зависимость для получения сервиса
async def get_sutochno_service() -> SutochnoService:
    async with SutochnoService() as service:
        yield service


@app.get("/", response_model=Dict[str, str])
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Platilka Hotel Booking Service",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/search/start", response_model=Dict[str, str])
async def start_search(
        booking_request: BookingRequest,
        background_tasks: BackgroundTasks,
        service: SutochnoService = Depends(get_sutochno_service)
):
    """
    Запуск поиска отелей в фоновом режиме

    Возвращает task_id для отслеживания прогресса
    """
    # Валидация дат
    if booking_request.check_in <= date.today():
        raise HTTPException(
            status_code=400,
            detail="Дата заезда должна быть не раньше завтрашнего дня"
        )

    if booking_request.check_out <= booking_request.check_in:
        raise HTTPException(
            status_code=400,
            detail="Дата выезда должна быть позже даты заезда"
        )

    # Генерируем уникальный ID задачи
    task_id = str(uuid.uuid4())

    # Инициализируем состояние задачи
    search_tasks[task_id] = {
        "status": "searching",
        "progress": 0,
        "message": "Начинаем поиск отелей...",
        "booking_request": booking_request,
        "result": None,
        "error": None,
        "created_at": datetime.now()
    }

    # Запускаем поиск в фоновом режиме
    background_tasks.add_task(perform_search, task_id, booking_request, service)

    logger.info(f"Запущен поиск отелей с task_id: {task_id}")

    return {"task_id": task_id, "message": "Поиск запущен"}


async def perform_search(task_id: str, booking_request: BookingRequest, service: SutochnoService):
    """Выполняет поиск отелей в фоновом режиме"""
    try:
        # Обновляем прогресс
        search_tasks[task_id]["progress"] = 10
        search_tasks[task_id]["message"] = "Открываем браузер..."

        # Выполняем поиск
        search_tasks[task_id]["progress"] = 30
        search_tasks[task_id]["message"] = "Ищем отели на sutochno.ru..."

        result = await service.search_hotels(booking_request)

        # Завершаем поиск
        search_tasks[task_id]["status"] = "completed"
        search_tasks[task_id]["progress"] = 100
        search_tasks[task_id]["message"] = f"Найдено {len(result.hotels)} отелей"
        search_tasks[task_id]["result"] = result

        logger.info(f"Поиск {task_id} завершен успешно")

    except Exception as e:
        # Обрабатываем ошибку
        search_tasks[task_id]["status"] = "error"
        search_tasks[task_id]["message"] = f"Ошибка при поиске: {str(e)}"
        search_tasks[task_id]["error"] = str(e)

        logger.error(f"Ошибка в поиске {task_id}: {e}")


@app.get("/search/{task_id}/status", response_model=SearchStatus)
async def get_search_status(task_id: str):
    """Получить статус поиска по task_id"""
    if task_id not in search_tasks:
        raise HTTPException(status_code=404, detail="Задача поиска не найдена")

    task_data = search_tasks[task_id]
    return SearchStatus(
        status=task_data["status"],
        message=task_data["message"],
        progress=task_data["progress"]
    )


@app.get("/search/{task_id}/results", response_model=HotelRecommendations)
async def get_search_results(task_id: str):
    """Получить результаты поиска по task_id"""
    if task_id not in search_tasks:
        raise HTTPException(status_code=404, detail="Задача поиска не найдена")

    task_data = search_tasks[task_id]

    if task_data["status"] == "searching":
        raise HTTPException(status_code=202, detail="Поиск еще выполняется")

    if task_data["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при поиске: {task_data['error']}"
        )

    if not task_data["result"]:
        raise HTTPException(status_code=404, detail="Результаты не найдены")

    return task_data["result"]


@app.post("/search", response_model=HotelRecommendations)
async def search_hotels_sync(
        booking_request: BookingRequest,
        service: SutochnoService = Depends(get_sutochno_service)
):
    """
    Синхронный поиск отелей (для простых запросов)

    ВНИМАНИЕ: Может занять много времени, используйте /search/start для больших запросов
    """
    try:
        result = await service.search_hotels(booking_request)
        return result
    except Exception as e:
        logger.error(f"Ошибка при синхронном поиске: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/booking/confirm", response_model=BookingConfirmation)
async def confirm_booking(
        hotel_id: str,
        task_id: str,
        booking_request: BookingRequest
):
    """
    Подтверждение выбора отеля для бронирования

    Сохраняет выбор пользователя и возвращает детали для финального подтверждения
    """
    # Проверяем, что поиск завершен
    if task_id not in search_tasks:
        raise HTTPException(status_code=404, detail="Задача поиска не найдена")

    task_data = search_tasks[task_id]
    if task_data["status"] != "completed" or not task_data["result"]:
        raise HTTPException(status_code=400, detail="Поиск не завершен или отсутствуют результаты")

    # Находим выбранный отель
    result: HotelRecommendations = task_data["result"]
    selected_hotel = None

    for hotel in result.hotels:
        if hotel.id == hotel_id:
            selected_hotel = hotel
            break

    if not selected_hotel:
        raise HTTPException(status_code=404, detail="Отель не найден в результатах поиска")

    # Создаем подтверждение бронирования
    confirmation_id = str(uuid.uuid4())
    confirmation = BookingConfirmation(
        hotel=selected_hotel,
        booking_request=booking_request,
        confirmed=False
    )

    booking_confirmations[confirmation_id] = confirmation

    logger.info(f"Создано подтверждение бронирования: {confirmation_id}")

    # Возвращаем подтверждение с ID
    return {
        "confirmation_id": confirmation_id,
        "hotel": selected_hotel,
        "booking_request": booking_request,
        "confirmed": False
    }


@app.post("/booking/{confirmation_id}/execute", response_model=BookingResult)
async def execute_booking(
        confirmation_id: str,
        service: SutochnoService = Depends(get_sutochno_service)
):
    """
    Выполнение фактического бронирования после подтверждения пользователя
    """
    if confirmation_id not in booking_confirmations:
        raise HTTPException(status_code=404, detail="Подтверждение бронирования не найдено")

    confirmation = booking_confirmations[confirmation_id]

    try:
        # Выполняем бронирование
        result = await service.book_hotel(confirmation.hotel, confirmation.booking_request)

        # Помечаем подтверждение как выполненное
        confirmation.confirmed = True

        logger.info(f"Бронирование {confirmation_id} выполнено: {result.success}")

        return result

    except Exception as e:
        logger.error(f"Ошибка при выполнении бронирования {confirmation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/booking/{confirmation_id}", response_model=BookingConfirmation)
async def get_booking_confirmation(confirmation_id: str):
    """Получить детали подтверждения бронирования"""
    if confirmation_id not in booking_confirmations:
        raise HTTPException(status_code=404, detail="Подтверждение бронирования не найдено")

    return booking_confirmations[confirmation_id]


@app.delete("/search/{task_id}")
async def cancel_search(task_id: str):
    """Отменить задачу поиска"""
    if task_id not in search_tasks:
        raise HTTPException(status_code=404, detail="Задача поиска не найдена")

    # Помечаем задачу как отмененную
    search_tasks[task_id]["status"] = "cancelled"
    search_tasks[task_id]["message"] = "Поиск отменен пользователем"

    logger.info(f"Поиск {task_id} отменен")

    return {"message": "Поиск отменен"}


@app.get("/cities", response_model=List[str])
async def get_supported_cities():
    """Получить список поддерживаемых городов"""
    # TODO: Реализовать получение списка городов из sutochno.ru
    cities = [
        "москва", "санкт-петербург", "новосибирск", "екатеринбург",
        "нижний-новгород", "казань", "челябинск", "омск", "самара",
        "ростов-на-дону", "уфа", "красноярск", "воронеж", "пермь"
    ]
    return cities


# Обработчики ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Обработчик HTTP ошибок"""
    return ErrorResponse(
        error=exc.detail,
        code=str(exc.status_code)
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Обработчик общих ошибок"""
    logger.error(f"Неожиданная ошибка: {exc}")
    return ErrorResponse(
        error="Внутренняя ошибка сервера",
        code="500",
        details={"message": str(exc)}
    )