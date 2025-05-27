from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PriceRange(BaseModel):
    """Модель для диапазона цен"""
    min_price: Optional[float] = Field(None, description="Минимальная цена")
    max_price: Optional[float] = Field(None, description="Максимальная цена")
    currency: str = Field("RUB", description="Валюта")


class ProductCategory(str, Enum):
    """Перечисление категорий товаров"""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    HOME = "home"
    BEAUTY = "beauty"
    SPORTS = "sports"
    BOOKS = "books"
    TOYS = "toys"
    FOOD = "food"
    OTHER = "other"


class ProductRequest(BaseModel):
    """Запрос на поиск товара"""
    query: str = Field(..., description="Основной поисковый запрос")
    city: str = Field(..., description="Город, в который нужно будет доставить продукт")
    category: Optional[ProductCategory] = Field(None, description="Категория товара")
    price_range: Optional[PriceRange] = Field(None, description="Диапазон цен")
    brand: Optional[str] = Field(None, description="Предпочтительный бренд")
    features: Optional[List[str]] = Field(None, description="Необходимые характеристики/функции")
    exclude_features: Optional[List[str]] = Field(None, description="Нежелательные характеристики/функции")
    # sort_by: Optional[str] = Field(None, description="Критерий сортировки")
    marketplaces: Optional[List[str]] = Field(None, description="Предпочтительные маркетплейсы")
    max_results: int = Field(5, description="Максимальное количество результатов")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Смартфон",
                "category": "electronics",
                "price_range": {
                    "min_price": 15000,
                    "max_price": 30000,
                    "currency": "RUB"
                },
                "brand": "Samsung",
                "features": ["NFC", "5G", "быстрая зарядка"],
                "exclude_features": ["refurbished"],
                "sort_by": "rating",
                "marketplaces": ["Яндекс.Маркет", "Ozon"],
                "max_results": 3
            }
        }


class Product(BaseModel):
    """Модель товара"""
    name: str = Field(..., description="Название товара")
    description: Optional[str] = Field(None, description="Описание товара")
    price: float = Field(..., description="Цена товара")
    currency: str = Field("RUB", description="Валюта")
    image_url: Optional[str] = Field(None, description="URL изображения товара")
    product_url: str = Field(..., description="URL страницы товара")
    marketplace: str = Field(..., description="Название маркетплейса")
    rating: Optional[float] = Field(None, description="Рейтинг товара")
    reviews_count: Optional[int] = Field(None, description="Количество отзывов")
    features: Optional[Dict[str, Any]] = Field(None, description="Характеристики товара")
    availability: Optional[str] = Field(None, description="Доступность товара")


class ProductRecommendation(BaseModel):
    """Модель для рекомендации товара"""
    product: Product = Field(..., description="Информация о товаре")
    relevance_score: float = Field(..., description="Оценка релевантности запросу")
    recommendation_reason: str = Field(..., description="Причина рекомендации")


class ProductRecommendationsResponse(BaseModel):
    """Ответ с рекомендациями товаров"""
    recommendations: List[ProductRecommendation] = Field(..., description="Список рекомендаций")
    query_details: ProductRequest = Field(..., description="Детали запроса")
    additional_questions: Optional[List[str]] = Field(None, description="Дополнительные вопросы для уточнения запроса")


class MissingInformationRequest(BaseModel):
    """Запрос на получение недостающей информации"""
    original_request: ProductRequest = Field(..., description="Исходный запрос пользователя")
    missing_fields: List[str] = Field(..., description="Список недостающих полей")


class MissingInformationResponse(BaseModel):
    """Ответ с запросом недостающей информации"""
    questions: List[str] = Field(..., description="Вопросы для получения недостающей информации")
    original_request: ProductRequest = Field(..., description="Исходный запрос пользователя")