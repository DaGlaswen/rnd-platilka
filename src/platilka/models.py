from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime, date
from enum import Enum


class PaymentMethod(str, Enum):
    """Способы оплаты"""
    CARD = "card"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"


class GuestInfo(BaseModel):
    """Информация о госте"""
    first_name: str = Field(..., description="Имя")
    last_name: str = Field(..., description="Фамилия")
    middle_name: Optional[str] = Field(None, description="Отчество")
    phone: str = Field(..., description="Телефон")
    email: str = Field(..., description="Email")


class PaymentInfo(BaseModel):
    """Информация об оплате"""
    card_number: Optional[str] = Field(None, description="Номер карты")
    card_holder: Optional[str] = Field(None, description="Держатель карты")
    expiry_month: Optional[int] = Field(None, ge=1, le=12, description="Месяц истечения")
    expiry_year: Optional[int] = Field(None, description="Год истечения")
    cvv: Optional[str] = Field(None, description="CVV код")
    method: PaymentMethod = Field(PaymentMethod.CARD, description="Способ оплаты")


class BookingRequest(BaseModel):
    """Запрос на бронирование"""
    city: str = Field(..., description="Город")
    check_in: date = Field(..., description="Дата заезда")
    check_out: date = Field(..., description="Дата выезда")
    guests_count: int = Field(1, ge=1, le=10, description="Количество гостей")

    # Опциональные параметры для фильтрации
    min_price: Optional[int] = Field(None, ge=0, description="Минимальная цена за ночь")
    max_price: Optional[int] = Field(None, ge=0, description="Максимальная цена за ночь")
    apartment_type: Optional[str] = Field(None, description="Тип жилья")
    amenities: Optional[List[str]] = Field(None, description="Удобства")
    district: Optional[str] = Field(None, description="Район")

    # Обязательная информация для бронирования
    guest_info: GuestInfo = Field(..., description="Информация о госте")
    payment_info: PaymentInfo = Field(..., description="Платежная информация")

    @validator('check_out')
    def check_out_after_check_in(cls, v, values):
        if 'check_in' in values and v <= values['check_in']:
            raise ValueError('Дата выезда должна быть позже даты заезда')
        return v

    @validator('max_price')
    def max_price_greater_than_min(cls, v, values):
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v <= values['min_price']:
                raise ValueError('Максимальная цена должна быть больше минимальной')
        return v


class HotelAmenity(BaseModel):
    """Удобство в отеле"""
    name: str = Field(..., description="Название удобства")
    available: bool = Field(..., description="Доступно ли")


class HotelInfo(BaseModel):
    """Информация об отеле/квартире"""
    id: str = Field(..., description="ID объекта")
    title: str = Field(..., description="Название")
    description: Optional[str] = Field(None, description="Описание")
    price_per_night: int = Field(..., description="Цена за ночь")
    total_price: int = Field(..., description="Общая стоимость")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Рейтинг")
    reviews_count: Optional[int] = Field(None, ge=0, description="Количество отзывов")

    # Локация
    address: str = Field(..., description="Адрес")
    district: Optional[str] = Field(None, description="Район")

    # Характеристики
    rooms_count: Optional[int] = Field(None, ge=1, description="Количество комнат")
    guests_capacity: int = Field(..., ge=1, description="Вместимость")

    # Удобства
    amenities: List[HotelAmenity] = Field(default_factory=list, description="Удобства")

    # Бесплатная отмена
    free_cancellation: bool = Field(..., description="Бесплатная отмена")
    cancellation_policy: Optional[str] = Field(None, description="Политика отмены")

    # Фотографии
    photos: List[str] = Field(default_factory=list, description="URL фотографий")

    # URL объекта
    url: str = Field(..., description="Ссылка на объект")


class HotelRecommendations(BaseModel):
    """Список рекомендуемых отелей"""
    hotels: List[HotelInfo] = Field(..., description="Список отелей")
    total_found: int = Field(..., description="Общее количество найденных вариантов")
    search_params: BookingRequest = Field(..., description="Параметры поиска")


class BookingConfirmation(BaseModel):
    """Подтверждение бронирования"""
    hotel: HotelInfo = Field(..., description="Выбранный отель")
    booking_request: BookingRequest = Field(..., description="Запрос на бронирование")
    confirmed: bool = Field(False, description="Подтверждено ли пользователем")


class BookingResult(BaseModel):
    """Результат бронирования"""
    success: bool = Field(..., description="Успешно ли прошло бронирование")
    booking_id: Optional[str] = Field(None, description="ID бронирования")
    confirmation_number: Optional[str] = Field(None, description="Номер подтверждения")
    total_amount: int = Field(..., description="Итоговая сумма")
    message: str = Field(..., description="Сообщение о результате")
    booking_url: Optional[str] = Field(None, description="Ссылка на бронирование")


class SearchStatus(BaseModel):
    """Статус поиска"""
    status: Literal["searching", "completed", "error"] = Field(..., description="Статус")
    message: str = Field(..., description="Описание статуса")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Прогресс в процентах")


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    error: str = Field(..., description="Описание ошибки")
    code: Optional[str] = Field(None, description="Код ошибки")
    details: Optional[dict] = Field(None, description="Дополнительные детали")