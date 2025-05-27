import logging

from fastapi import APIRouter, Depends, HTTPException, status

from platilka.models.product import (
    ProductRequest,
    ProductRecommendationsResponse,
    MissingInformationResponse
)
from platilka.services.product_service import ProductService

# Создаем роутер
router = APIRouter()


# Зависимость для сервиса товаров
async def get_product_service() -> ProductService:
    """Возвращает экземпляр сервиса товаров"""
    async with ProductService() as service:
        yield service


@router.post(
    "/recommendations",
    response_model=ProductRecommendationsResponse,
    summary="Получить рекомендации товаров",
    description="Получает рекомендации товаров на основе запроса пользователя"
)
async def get_product_recommendations(
        request: ProductRequest,
        product_service: ProductService = Depends(get_product_service)
) -> ProductRecommendationsResponse:
    """
    Получает рекомендации товаров на основе запроса пользователя

    - **query**: Основной поисковый запрос
    - **city**: Город
    - **category**: Категория товара (опционально)
    - **price_range**: Диапазон цен (опционально)
    - **brand**: Предпочтительный бренд (опционально)
    - **features**: Необходимые характеристики/функции (опционально)
    - **exclude_features**: Нежелательные характеристики/функции (опционально)
    - **sort_by**: Критерий сортировки (опционально)
    - **marketplaces**: Предпочтительные маркетплейсы (опционально)
    - **max_results**: Максимальное количество результатов (по умолчанию 5)
    """
    try:
        # Анализируем запрос и проверяем, достаточно ли информации
        # missing_info = await product_service.analyze_request(request)
        #
        # if missing_info:
        #     # Если недостаточно информации, возвращаем 422 с вопросами для уточнения
        #     raise HTTPException(
        #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        #         detail={
        #             "message": "Необходима дополнительная информация",
        #             "questions": missing_info.questions,
        #             "original_request": request.model_dump()
        #         }
        #     )

        # Получаем рекомендации товаров
        recommendations = await product_service.get_product_recommendations(request)
        return recommendations

    except HTTPException:
        # Пробрасываем HTTPException дальше
        raise
    except Exception as e:
        # Логируем ошибку и возвращаем 500
        logging.exception(f"Ошибка при получении рекомендаций: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении рекомендаций: {str(e)}"
        )


# @router.post(
#     "/analyze",
#     response_model=MissingInformationResponse,
#     summary="Анализировать запрос",
#     description="Анализирует запрос пользователя и возвращает недостающую информацию"
# )
# async def analyze_request(
#         request: ProductRequest,
#         product_service: ProductService = Depends(get_product_service)
# ) -> MissingInformationResponse:
#     """
#     Анализирует запрос пользователя и возвращает недостающую информацию
#
#     - **request**: Запрос пользователя
#     """
#     try:
#         # Анализируем запрос
#         missing_info = await product_service.analyze_request(request)
#
#         if not missing_info:
#             # Если информации достаточно, возвращаем пустой список вопросов
#             return MissingInformationResponse(
#                 questions=[],
#                 original_request=request
#             )
#
#         return missing_info
#
#     except Exception as e:
#         # Логируем ошибку и возвращаем 500
#         import logging
#         logging.error(f"Ошибка при анализе запроса: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Ошибка при анализе запроса: {str(e)}"
#         )
