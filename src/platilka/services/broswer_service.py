import asyncio
import json
from typing import Optional, List

from browser_use import Agent, Browser
from langchain_groq import ChatGroq
from browser_use import Browser, BrowserContextConfig, BrowserConfig

from platilka.core.logging import logger
from platilka.core.settings import settings
from platilka.models.product import Product, ProductRequest

browser = Browser(
            config=BrowserConfig(
                headless=False,
                disable_security=False,
                # keep_alive=True,
                new_context_config=BrowserContextConfig(
                    # keep_alive=True,
                    disable_security=False,
                ),
            )
        )

class BrowserService:
    """Сервис для работы с браузером через browser-use"""

    def __init__(self, groq_api_key: str = None):
        """
        Инициализирует сервис браузера

        Args:
            groq_api_key: API-ключ для Groq (если не указан, берется из настроек)
        """
        self.browser: Optional[Browser] = browser
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        self.llm = ChatGroq(
            groq_api_key=self.groq_api_key,
            model_name=settings.LLM_MODEL_NAME,
            temperature=0.5,
        )

    async def create_agent(self, task: str) -> Agent:
        """
        Создает новый экземпляр агента browser-use

        Returns:
            Настроенный агент браузера
        """
        agent = Agent(
            task=task,
            llm=self.llm,
            # Настройки браузера
            browser=self.browser,
            # use_vision=False
        )
        return agent

    async def extract_product_info(self, url: str, request: ProductRequest) -> Optional[Product]:
        """
        Извлекает информацию о товаре со страницы

        Args:
            url: URL страницы товара

        Returns:
            Информация о товаре или None в случае ошибки
            :param request:
        """
        logger.info(f"Извлечение информации о товаре с URL: {url}")

        try:
            # Формируем промпт для извлечения информации о товаре
            extraction_prompt = f"""
            Перейди на страницу {url}. Если это не страница конкретного одного продукта. Перейди на первую страницу продукта в списке в каталоге.
            Если потребуется выбрать город/регион, выбирай {request.city}
            Извлеки следующую информацию о товаре:

            1. Название товара
            2. Описание товара
            3. Цена товара (найди актуальную цену, обрати внимание на скидки)
            4. Валюта цены
            5. URL главного изображения товара
            6. Рейтинг товара (если есть)
            7. Количество отзывов (если есть)
            8. Основные характеристики товара
            9. Доступность товара (в наличии, под заказ, нет в наличии и т.д.)

            Не совершай лишних действий. Извлекай только то, о чем я тебя попросил. Будь внимателен к деталям и извлеки максимально точную информацию.

            Верни результат в следующем JSON формате:
            {{
                "name": "Название товара",
                "description": "Описание товара",
                "price": 10000.0,
                "currency": "RUB",
                "image_url": "https://example.com/image.jpg",
                "rating": 4.5,
                "reviews_count": 123,
                "features": {{
                    "характеристика1": "значение1",
                    "характеристика2": "значение2"
                }},
                "availability": "В наличии"
            }}

            Если какая-то информация недоступна, указывай null для соответствующего поля.
            """

            agent = await self.create_agent(task=extraction_prompt)

            # Выполняем задачу извлечения информации
            result = await agent.run()

            extracted_content = result.history[-1].result[0].extracted_content
            # Парсим результат
            try:
                # Извлекаем JSON из результата
                if isinstance(extracted_content, str):
                    # Ищем JSON в тексте результата
                    start_idx = extracted_content.find('{')
                    end_idx = extracted_content.rfind('}') + 1
                    if start_idx != -1 and end_idx != 0:
                        json_str = extracted_content[start_idx:end_idx]
                        product_data = json.loads(json_str)
                    else:
                        logger.error(f"Не удалось найти JSON в результате: {extracted_content}")
                        return None
                else:
                    product_data = extracted_content

                # Создаем объект Product
                product = Product(
                    name=product_data.get("name", ""),
                    description=product_data.get("description"),
                    price=float(product_data.get("price", 0)),
                    currency=product_data.get("currency", "RUB"),
                    image_url=product_data.get("image_url"),
                    product_url=url,
                    marketplace=self._extract_marketplace_name(url),
                    rating=product_data.get("rating"),
                    reviews_count=product_data.get("reviews_count"),
                    features=product_data.get("features"),
                    availability=product_data.get("availability")
                )

                logger.info(f"Успешно извлечена информация о товаре: {product.name}")
                return product

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON результата: {str(e)}")
                logger.debug(f"Результат агента: {result}")
                raise e

        except Exception as e:
            logger.error(f"Ошибка при извлечении информации о товаре с {url}: {str(e)}")
            raise e

    async def extract_multiple_products(self, urls: List[str], request: ProductRequest) -> List[Product]:
        """
        Извлекает информацию о товарах с нескольких страниц

        Args:
            urls: Список URL страниц товаров

        Returns:
            Список товаров с извлеченной информацией
            :param request:
        """
        logger.info(f"Извлечение информации о товарах с {len(urls)} страниц")

        # Ограничиваем количество одновременных запросов
        # semaphore = asyncio.Semaphore(3)

        async def extract_single_product(url: str) -> Optional[Product]:
            try:
                return await self.extract_product_info(url, request)
            except Exception as e:
                logger.error(f"Ошибка при обработке URL {url}: {str(e)}")
                return None

        # Создаем и запускаем все задачи одновременно
        tasks = [extract_single_product(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Фильтруем None результаты (которые возникли из-за ошибок)
        products = [product for product in results if product is not None]

        logger.info(f"Успешно извлечена информация о {len(products)} товарах из {len(urls)}")
        return products

    def _extract_marketplace_name(self, url: str) -> str:
        """
        Извлекает название маркетплейса из URL

        Args:
            url: URL страницы

        Returns:
            Название маркетплейса
        """
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # Убираем www. и другие поддомены
        domain_parts = domain.split('.')
        if len(domain_parts) > 2 and domain_parts[0] in ['www', 'm', 'mobile']:
            domain = '.'.join(domain_parts[1:])

        # Преобразуем в читаемое название маркетплейса
        marketplace_mapping = {
            "ozon.ru": "Ozon",
            "ozon.com": "Ozon",
            "wildberries.ru": "Wildberries",
            "wb.ru": "Wildberries",
            "market.yandex.ru": "Яндекс.Маркет",
            "yandex.ru": "Яндекс.Маркет",
            "dns-shop.ru": "DNS",
            "mvideo.ru": "М.Видео",
            "eldorado.ru": "Эльдорадо",
            "citilink.ru": "Ситилинк",
            "lamoda.ru": "Lamoda",
            "aliexpress.ru": "AliExpress",
            "aliexpress.com": "AliExpress",
            "sbermegamarket.ru": "СберМегаМаркет",
            "sber.ru": "СберМегаМаркет",
            "avito.ru": "Avito",
            "kupivip.ru": "KupiVIP",
            "sportmaster.ru": "Спортмастер"
        }

        return marketplace_mapping.get(domain, domain)

    async def close(self):
        """Закрывает соединения и очищает ресурсы"""
        # В текущей версии browser-use автоматически управляет жизненным циклом браузера
        pass
