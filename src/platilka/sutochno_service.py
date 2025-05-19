from typing import List, Optional, Any

from browser_use import Agent, Browser
from langchain_groq import ChatGroq
from loguru import logger

from .models import (
    BookingRequest, HotelInfo, HotelRecommendations,
    BookingResult
)
from .settings import settings


class SutochnoService:
    """Сервис для работы с сайтом sutochno.ru"""

    def __init__(self):
        self.llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.llm_model,
            temperature=settings.llm_temperature
        )
        self.browser: Optional[Browser] = None
        self.agent: Optional[Agent] = None

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.browser = Browser(
            # headless=settings.browser_headless,
            # timeout=settings.browser_timeout
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.browser:
            await self.browser.close()

    async def init_agent_with_task(self, task: str):
        self.agent = Agent(
            task=task,
            llm=self.llm,
            browser=self.browser
        )

    async def search_hotels(self, booking_request: BookingRequest) -> HotelRecommendations:
        """
        Поиск отелей на sutochno.ru

        Args:
            booking_request: Запрос на бронирование

        Returns:
            HotelRecommendations: Список найденных отелей
        """
        logger.info(f"Начинаем поиск отелей для города {booking_request.city}")

        # Формируем URL для поиска
        # search_url = self._build_search_url(booking_request)
        # logger.info(f"URL поиска: {search_url}")

        # Задача для агента
        search_task = f"""
        
        Шаг 1:
        Перейди на сайт {settings.sutochno_base_url} и найди отели для бронирования.

        Шаг 2:
        Введи следующие параметры поиска:
        - Город: {booking_request.city}
        - Дата заезда: {booking_request.check_in}
        - Дата выезда: {booking_request.check_out}
        - Количество гостей: {booking_request.guests_count}

        Шаг 3: 
        Дождись прогрузки страницы с результатами
        
        Шаг 4:
        Заполни и примени фильтр 'Цена за сутки' значениями от '{booking_request.min_price}' до '{booking_request.max_price}'
        
        Шаг 5:
        Дождись пока страница обновится после применения фильтра 
        
        Шаг 6:
        Пройдись в цикле по первым 5 результатам поиска. Для каждого объекта зайди на его страницу и извлеки:
           - Название
           - Цену за ночь
           - Общую стоимость
           - Рейтинг (если есть)
           - Количество отзывов
           - Адрес
           - Количество комнат/гостей
           - Удобства
           - Ссылку на объект
           - URL первой фотографии
           
        При необходимости мотай страницу вниз
    
        Шаг 7:
        Ограничь результат {settings.max_search_results} лучшими вариантами

        Верни результат в формате JSON со списком найденных объектов.
        """

        try:
            # Устанавливаем задачу агенту
            await self.init_agent_with_task(search_task)

            # Выполняем поиск
            result = await self.agent.run()

            # Парсим результат
            hotels = await self._parse_search_results(result, booking_request)

            return HotelRecommendations(
                hotels=hotels,
                total_found=len(hotels),
                search_params=booking_request
            )

        except Exception as e:
            logger.error(f"Ошибка при поиске отелей: {e}")
            raise

    async def book_hotel(self, hotel: HotelInfo, booking_request: BookingRequest) -> BookingResult:
        """
        Бронирование выбранного отеля

        Args:
            hotel: Выбранный отель
            booking_request: Запрос на бронирование

        Returns:
            BookingResult: Результат бронирования
        """
        logger.info(f"Начинаем бронирование отеля {hotel.title}")

        booking_task = f"""
        Оформи бронирование на сайте sutochno.ru для отеля.

        Данные отеля:
        - Название: {hotel.title}
        - URL: {hotel.url}
        - Цена: {hotel.total_price} рублей

        Данные бронирования:
        - Дата заезда: {booking_request.check_in}
        - Дата выезда: {booking_request.check_out}
        - Количество гостей: {booking_request.guests_count}

        Данные гостя:
        - Имя: {booking_request.guest_info.first_name}
        - Фамилия: {booking_request.guest_info.last_name}
        - Отчество: {booking_request.guest_info.middle_name or ""}
        - Телефон: {booking_request.guest_info.phone}
        - Email: {booking_request.guest_info.email}

        Платежные данные:
        - Способ оплаты: {booking_request.payment_info.method}
        - Номер карты: {booking_request.payment_info.card_number}
        - Держатель карты: {booking_request.payment_info.card_holder}
        - Срок действия: {booking_request.payment_info.expiry_month}/{booking_request.payment_info.expiry_year}
        - CVV: {booking_request.payment_info.cvv}

        Шаги:
        1. Перейди по ссылке отеля
        2. Нажми кнопку "Забронировать" или аналогичную
        3. Заполни все необходимые поля с данными гостя
        4. Введи платежную информацию
        5. Проверь детали бронирования
        6. Подтверди бронирование
        7. Получи номер подтверждения и сохрани его

        ВАЖНО: 
        - Убедись что выбрана опция "Бесплатная отмена"
        - Не завершай оплату, только заполни форму до момента финального подтверждения
        - Верни номер бронирования и все детали в формате JSON
        """

        try:
            # Устанавливаем задачу агенту
            self.agent.task = booking_task

            # Выполняем бронирование
            result = await self.agent.run()

            # Парсим результат бронирования
            booking_result = await self._parse_booking_result(result, hotel, booking_request)

            return booking_result

        except Exception as e:
            logger.error(f"Ошибка при бронировании: {e}")
            return BookingResult(
                success=False,
                total_amount=hotel.total_price,
                message=f"Ошибка при бронировании: {str(e)}"
            )

    def _build_search_url(self, booking_request: BookingRequest) -> str:
        """Строит URL для поиска на sutochno.ru"""
        base_url = f"{settings.sutochno_base_url}"

        params = [
            f"term{booking_request.city}",
            f"price_per{booking_request.guests_county}",
            f"occupied={booking_request.check_in.strftime('%Y-%m-%d')};{booking_request.check_out.strftime('%Y-%m-%d')}",
            f"checkout={booking_request.check_out.strftime('%Y-%m-%d')}",
            f"guests_adults={booking_request.guests_count}"
        ]

        # Добавляем фильтры если есть
        if booking_request.min_price:
            params.append(f"price_min={booking_request.min_price}")
        if booking_request.max_price:
            params.append(f"price_max={booking_request.max_price}")

        return f"{base_url}?{'&'.join(params)}"

    async def _parse_search_results(self, agent_result: Any, booking_request: BookingRequest) -> List[HotelInfo]:
        """Парсит результаты поиска от агента"""
        hotels = []

        try:
            # Здесь должна быть логика парсинга результата от агента
            # Пока что возвращаем пустой список
            # TODO: Реализовать парсинг JSON ответа от агента

            # Пример структуры, которую должен вернуть агент:
            # {
            #     "hotels": [
            #         {
            #             "title": "Уютная квартира в центре",
            #             "price_per_night": 3000,
            #             "total_price": 9000,
            #             "rating": 4.5,
            #             "reviews_count": 25,
            #             "address": "ул. Пушкина, 10",
            #             "guests_capacity": 4,
            #             "amenities": ["Wi-Fi", "Кухня", "Кондиционер"],
            #             "free_cancellation": true,
            #             "url": "https://sutochno.ru/...",
            #             "photos": ["https://..."]
            #         }
            #     ]
            # }

            logger.warning("Парсинг результатов поиска пока не реализован")

        except Exception as e:
            logger.error(f"Ошибка при парсинге результатов поиска: {e}")

        return hotels

    async def _parse_booking_result(self, agent_result: Any, hotel: HotelInfo,
                                    booking_request: BookingRequest) -> BookingResult:
        """Парсит результат бронирования от агента"""
        try:
            # TODO: Реализовать парсинг результата бронирования

            logger.warning("Парсинг результата бронирования пока не реализован")

            return BookingResult(
                success=False,
                total_amount=hotel.total_price,
                message="Парсинг результата бронирования пока не реализован"
            )

        except Exception as e:
            logger.error(f"Ошибка при парсинге результата бронирования: {e}")
            return BookingResult(
                success=False,
                total_amount=hotel.total_price,
                message=f"Ошибка при парсинге результата: {str(e)}"
            )
