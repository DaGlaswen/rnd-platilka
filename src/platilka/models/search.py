from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Модель результата поиска"""
    title: str = Field(..., description="Заголовок результата поиска")
    link: str = Field(..., description="URL страницы")
    snippet: Optional[str] = Field(None, description="Сниппет результата поиска")
    position: int = Field(..., description="Позиция в результатах поиска")
    source: str = Field(..., description="Источник (маркетплейс)")


class SerperSearchResponse(BaseModel):
    """Модель ответа от Serper API"""
    shopping: List[Dict[str, Any]] = Field(..., description="Органические результаты поиска")
    serpapi_pagination: Optional[Dict[str, Any]] = Field(None, description="Информация о пагинации")
    search_metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные поиска")

    def to_search_results(self) -> List[SearchResult]:
        """Преобразует ответ от Serper в список результатов поиска"""
        results = []
        for index, item in enumerate(self.shopping):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", None),
                    position=index + 1,
                    source=self._extract_source(item.get("link", ""))
                )
            )
        return results

    @staticmethod
    def _extract_source(url: str) -> str:
        """Извлекает название маркетплейса из URL"""
        # Простая реализация для извлечения домена
        import re
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        # Убираем www. и другие поддомены
        domain_parts = domain.split('.')
        if len(domain_parts) > 2:
            domain = '.'.join(domain_parts[-2:])

        # Преобразуем в читаемое название маркетплейса
        marketplace_mapping = {
            "ozon.ru": "Ozon",
            "wildberries.ru": "Wildberries",
            "market.yandex.ru": "Яндекс.Маркет",
            "dns-shop.ru": "DNS",
            "mvideo.ru": "М.Видео",
            "eldorado.ru": "Эльдорадо",
            "citilink.ru": "Ситилинк",
            "lamoda.ru": "Lamoda",
            "aliexpress.ru": "AliExpress",
            "sbermegamarket.ru": "СберМегаМаркет"
        }

        return marketplace_mapping.get(domain, domain)


class SearchRequest(BaseModel):
    """Модель запроса к поисковой системе"""
    query: str = Field(..., description="Поисковый запрос")
    marketplace_hints: Optional[List[str]] = Field(None, description="Подсказки по маркетплейсам")
    num_results: int = Field(10, description="Количество результатов")

    def build_search_query(self) -> str:
        """Формирует поисковый запрос с учетом маркетплейсов"""
        if not self.marketplace_hints:
            return f"{self.query} купить интернет-магазин"

        marketplace_str = " OR ".join([f"site:{marketplace}" for marketplace in self.marketplace_hints])
        return f"{self.query} ({marketplace_str})"