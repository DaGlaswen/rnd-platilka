import json
import os
import re
from typing import List, Optional, Tuple

from langchain.schema import HumanMessage
from langchain_groq import ChatGroq

from platilka.core.logging import logger
from platilka.core.settings import settings
from platilka.models.product import (
    ProductRequest,
    Product,
    ProductRecommendation,
    ProductRecommendationsResponse
)
from platilka.models.search import SearchRequest, SearchResult
from platilka.services.broswer_service import BrowserService
from platilka.services.search_service import SearchService
from platilka.utils.prompts import (
    # get_analyze_request_prompt,
    get_generate_search_query_prompt,
    get_evaluate_product_relevance_prompt,
    get_generate_recommendations_prompt
)


class ProductService:
    """Сервис для поиска и рекомендации товаров"""

    def __init__(self):
        """Инициализирует сервис рекомендации товаров"""
        # Инициализируем зависимые сервисы
        self.search_service = SearchService()
        self.browser_service = BrowserService()

        # Инициализируем Language Model
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY", settings.GROQ_API_KEY),
            model_name=settings.LLM_MODEL_NAME
        )

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        # self.browser_service.browser = browser

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.browser_service.browser:
            await self.browser_service.browser.close()

    async def generate_search_query(self, request: ProductRequest) -> str:
        """
        Генерирует поисковый запрос на основе запроса пользователя

        Args:
            request: Запрос пользователя

        Returns:
            Поисковый запрос для поиска товаров
        """
        logger.info(f"Генерация поискового запроса для: {request.query}")

        prompt = get_generate_search_query_prompt(request)
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])

        # Очищаем ответ от лишних кавычек
        search_query = response.content.strip().strip('"').strip("'").strip()
        logger.info(f"Сгенерирован поисковый запрос: {search_query}")

        return search_query

    async def search_products(
            self,
            request: ProductRequest
    ) -> List[SearchResult]:
        """
        Выполняет поиск товаров на основе запроса пользователя

        Args:
            request: Запрос пользователя

        Returns:
            Список результатов поиска
        """
        # Генерируем поисковый запрос
        search_query = await self.generate_search_query(request)

        # Создаем объект поискового запроса
        search_request = SearchRequest(
            query=search_query,
            marketplace_hints=request.marketplaces,
            num_results=settings.MAX_SEARCH_RESULTS
        )

        # Выполняем поиск
        return await self.search_service.search(search_request)

    async def evaluate_product_relevance(
            self,
            request: ProductRequest,
            product: Product
    ) -> Tuple[float, str]:
        """
        Оценивает релевантность товара запросу пользователя

        Args:
            request: Запрос пользователя
            product: Информация о товаре

        Returns:
            Кортеж (оценка релевантности, причина рекомендации)
        """
        prompt = get_evaluate_product_relevance_prompt(
            request=request,
            product_json=product.model_dump_json(indent=2)
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)], max_tokens=2000)

        try:
            # Извлекаем JSON из ответа
            logger.debug(f"Ответ от evaluate_product_relevance_prompt: {response.content}")
            response_json = self._extract_json_from_text(response.content)
            if not response_json:
                logger.warning("Не удалось извлечь JSON из ответа LLM при оценке товара")
                return 0.0, "Не удалось оценить релевантность товара"

            data = json.loads(response_json)
            relevance_score = float(data.get("relevance_score", 0.0))
            recommendation_reason = data.get("recommendation_reason", "")

            return relevance_score, recommendation_reason

        except Exception as e:
            logger.error(f"Ошибка при оценке релевантности товара: {str(e)}")
            return 0.0, f"Ошибка при оценке: {str(e)}"

    async def generate_recommendations(
            self,
            request: ProductRequest,
            evaluated_products: List[Tuple[Product, float, str]]
    ) -> ProductRecommendationsResponse:
        """
        Генерирует окончательные рекомендации на основе оцененных товаров

        Args:
            request: Запрос пользователя
            evaluated_products: Список кортежей (товар, оценка, причина)

        Returns:
            Ответ с рекомендациями товаров
        """
        # Формируем список оцененных товаров в формате JSON
        products_data = []
        for product, score, reason in evaluated_products:
            products_data.append({
                "product": product.model_dump(),
                "relevance_score": score,
                "recommendation_reason": reason
            })

        # Получаем промпт для генерации рекомендаций
        prompt = get_generate_recommendations_prompt(
            request=request,
            evaluated_products_json=json.dumps(products_data, indent=2, ensure_ascii=False),
            max_recommendations=request.max_results
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])

        try:
            # Извлекаем JSON из ответа
            response_json = self._extract_json_from_text(response.content)
            if not response_json:
                logger.warning("Не удалось извлечь JSON из ответа LLM при генерации рекомендаций")
                # Если не удалось извлечь JSON, формируем рекомендации вручную
                return self._fallback_recommendations(request, evaluated_products)

            data = json.loads(response_json)

            # Собираем объекты ProductRecommendation
            recommendations = []
            for rec_data in data.get("recommendations", []):
                product_data = rec_data.get("product", {})
                product = Product(**product_data)

                recommendations.append(
                    ProductRecommendation(
                        product=product,
                        relevance_score=rec_data.get("relevance_score", 0.0),
                        recommendation_reason=rec_data.get("recommendation_reason", "")
                    )
                )

            # Формируем итоговый ответ
            return ProductRecommendationsResponse(
                recommendations=recommendations,
                query_details=request,
                additional_questions=data.get("additional_questions", [])
            )

        except Exception as e:
            logger.error(f"Ошибка при генерации рекомендаций: {str(e)}")
            return self._fallback_recommendations(request, evaluated_products)

    def _fallback_recommendations(
            self,
            request: ProductRequest,
            evaluated_products: List[Tuple[Product, float, str]]
    ) -> ProductRecommendationsResponse:
        """
        Формирует резервные рекомендации в случае ошибки

        Args:
            request: Запрос пользователя
            evaluated_products: Список кортежей (товар, оценка, причина)

        Returns:
            Ответ с рекомендациями товаров
        """
        # Сортируем товары по релевантности
        evaluated_products.sort(key=lambda x: x[1], reverse=True)

        # Ограничиваем количество результатов
        top_products = evaluated_products[:request.max_results]

        # Формируем рекомендации
        recommendations = []
        for product, score, reason in top_products:
            recommendations.append(
                ProductRecommendation(
                    product=product,
                    relevance_score=score,
                    recommendation_reason=reason
                )
            )

        return ProductRecommendationsResponse(
            recommendations=recommendations,
            query_details=request,
            additional_questions=[]
        )

    async def get_product_recommendations(
            self,
            request: ProductRequest
    ) -> ProductRecommendationsResponse:
        """
        Основной метод для получения рекомендаций товаров

        Args:
            request: Запрос пользователя

        Returns:
            Ответ с рекомендациями товаров
        """
        logger.info(f"Получение рекомендаций для запроса: {request.query}")

        # Шаг 1: Выполняем поиск товаров
        search_results = await self.search_products(request)
        logger.info(f"Найдено {len(search_results)} потенциальных товаров")

        if not search_results:
            return ProductRecommendationsResponse(
                recommendations=[],
                query_details=request,
                additional_questions=["Попробуйте изменить запрос или расширить критерии поиска"]
            )

        # Шаг 2: Извлекаем информацию о товарах из топ-результатов
        # Ограничиваем количество результатов для обработки
        max_pages_to_process = min(len(search_results), settings.MAX_SEARCH_RESULTS)
        product_urls = [result.link for result in search_results[:max_pages_to_process]]

        products = await self.browser_service.extract_multiple_products(product_urls, request)
        logger.info(f"Успешно извлечена информация о {len(products)} товарах")

        if not products:
            return ProductRecommendationsResponse(
                recommendations=[],
                query_details=request,
                additional_questions=["Не удалось извлечь информацию о товарах. Попробуйте изменить запрос."]
            )

        # Шаг 3: Оцениваем релевантность каждого товара
        evaluated_products = []

        for product in products:
            score, reason = await self.evaluate_product_relevance(request, product)
            evaluated_products.append((product, score, reason))

        logger.info(f"Оценено {len(evaluated_products)} товаров")

        # Шаг 4: Генерируем рекомендации
        return await self.generate_recommendations(request, evaluated_products)

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Извлекает JSON из текста

        Args:
            text: Текст, содержащий JSON

        Returns:
            Строка с JSON или None, если не удалось извлечь
        """
        # Пытаемся найти JSON в тексте между ```json и ```
        json_pattern = r"```json\s*([\s\S]*?)\s*```"
        matches = re.findall(json_pattern, text)

        if matches:
            return matches[0].strip()

        # Если не удалось найти JSON между маркерами, пытаемся найти
        # любой текст, похожий на JSON-объект
        json_pattern = r"(\{[\s\S]*\})"
        matches = re.findall(json_pattern, text)

        if matches:
            return matches[0].strip()

        return None
