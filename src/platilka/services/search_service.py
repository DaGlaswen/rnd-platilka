import json
from typing import List, Optional

import httpx
import requests

from platilka.core.logging import logger
from platilka.core.settings import settings
from platilka.models.search import SearchRequest, SerperSearchResponse, SearchResult


class SearchService:
    """Сервис для выполнения поисковых запросов через Serper API"""

    def __init__(self, api_key: str = None):
        """
        Инициализирует сервис поиска

        Args:
            api_key: API-ключ для Serper (если не указан, берется из настроек)
        """
        self.api_key = api_key or settings.SERPER_API_KEY
        self.base_url = "https://google.serper.dev/shopping"
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

    async def search(self, search_request: SearchRequest) -> List[SearchResult]:
        """
        Выполняет поисковый запрос и возвращает результаты

        Args:
            search_request: Запрос на поиск

        Returns:
            Список результатов поиска
        """
        # query = search_request.build_search_query()
        logger.info(f"Выполняется поисковый запрос: {search_request.query}")

        payload = json.dumps({
            "q": search_request.query,
            "num": search_request.num_results,
            "location": "Russia",
            "gl": "ru",
            "hl": "ru"
        })

        try:

            # url = "https://google.serper.dev/search"
            #
            # payload2 = json.dumps({
            #     "q": "Hankook Ventus Pro 21 275/45 R 315/40 R цена от 25000 до 45000 рублей"
            # })
            # headers = {
            #     'X-API-KEY': 'ea42b3067724311d8b47844ca545cbe0719bb246',
            #     'Content-Type': 'application/json'
            # }
            #
            # response = requests.request("POST", url, headers=headers, data=payload2)
            # logger.debug(response.text)
            # response.raise_for_status()
            # data = response.json()
            # search_response = SerperSearchResponse(**data)
            # results = search_response.to_search_results()
            # logger.info(f"Получено {len(results)} результатов поиска")
            # # return results



            response = requests.request("POST", self.base_url, headers=self.headers, data=payload)
            logger.debug(f"Ответ от SERPER {response.text}")
            response.raise_for_status()
            data = response.json()
            search_response = SerperSearchResponse(**data)
            results = search_response.to_search_results()
            logger.info(f"Получено {len(results)} результатов поиска")
            return results

        except httpx.RequestError as e:
            logger.error(f"Ошибка при выполнении запроса к Serper API: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Serper API вернул ошибку: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            raise

    async def search_products(
            self,
            query: str,
            marketplaces: Optional[List[str]] = None,
            num_results: int = 10
    ) -> List[SearchResult]:
        """
        Удобный метод для поиска товаров

        Args:
            query: Поисковый запрос
            marketplaces: Список маркетплейсов для фильтрации результатов
            num_results: Количество результатов

        Returns:
            Список результатов поиска
        """
        search_request = SearchRequest(
            query=query,
            marketplace_hints=marketplaces,
            num_results=num_results
        )

        return await self.search(search_request)
