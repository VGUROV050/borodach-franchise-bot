# Bitrix API client

import logging
from typing import Any

import httpx

from config.settings import BITRIX_WEBHOOK_URL

logger = logging.getLogger(__name__)

# Таймауты для запросов к Bitrix
TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class BitrixClientError(Exception):
    """Ошибка при работе с Bitrix API."""
    pass


async def call_method(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Вызвать метод Bitrix24 REST API.
    
    Args:
        method: Название метода (например, 'tasks.task.add')
        params: Параметры запроса
        
    Returns:
        Ответ от Bitrix в виде словаря
        
    Raises:
        BitrixClientError: При ошибке запроса или ответа
    """
    if not BITRIX_WEBHOOK_URL:
        raise BitrixClientError("BITRIX_WEBHOOK_URL не настроен")
    
    url = f"{BITRIX_WEBHOOK_URL.rstrip('/')}/{method}"
    
    logger.info(f"Bitrix API call: {method}")
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json=params or {})
            
            logger.info(f"Bitrix response: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Bitrix HTTP error: {response.status_code} - {response.text[:200]}")
                raise BitrixClientError(f"HTTP {response.status_code}")
            
            data = response.json()
            
            # Bitrix возвращает ошибки в поле "error"
            if "error" in data:
                error_msg = data.get("error_description", data["error"])
                logger.error(f"Bitrix API error: {error_msg}")
                raise BitrixClientError(error_msg)
            
            return data
            
    except httpx.RequestError as e:
        logger.error(f"Bitrix network error: {e}")
        raise BitrixClientError(f"Ошибка сети: {e}") from e
