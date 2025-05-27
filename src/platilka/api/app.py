from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from platilka.api.endpoints import product_recommendations
from platilka.core.settings import settings

# Инициализируем FastAPI приложение
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Настраиваем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем основной роутер
api_router = APIRouter()

# Добавляем роутеры для различных эндпоинтов
api_router.include_router(
    product_recommendations.router,
    prefix="/products",
    tags=["products"],
)

# Подключаем основной роутер к приложению
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["root"])
async def root():
    """Корневой эндпоинт с информацией о сервисе"""
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "description": "Сервис рекомендации товаров в интернет-магазинах и маркетплейсах",
        "docs_url": f"{settings.API_V1_STR}/docs",
    }