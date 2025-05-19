"""
Platilka Hotel Booking Service

Сервис автоматического бронирования отелей на sutochno.ru
с использованием browser-use и FastAPI.
"""

__version__ = "0.1.0"
__author__ = "glaswennn"
__email__ = "golovinov.daniel@gmail.com"

from .api import app
from .models import *
from .settings import settings
from .sutochno_service import SutochnoService

__all__ = [
    "app",
    "settings",
    "SutochnoService",
    "BookingRequest",
    "HotelInfo",
    "HotelRecommendations",
    "BookingResult",
    "BookingConfirmation",
]