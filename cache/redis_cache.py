# Redis caching implementation

import json
from typing import Any, Optional, List, Dict
from datetime import timedelta

import redis.asyncio as redis

from config.settings import REDIS_URL
from config.logging import get_logger

logger = get_logger(__name__)

# Глобальный клиент Redis
_redis_client: Optional[redis.Redis] = None

# Время жизни кэша (в секундах)
CACHE_TTL = {
    "network_rating": 3600,      # 1 час — рейтинг сети
    "companies": 900,            # 15 минут — список салонов
    "partner_stats": 300,        # 5 минут — статистика партнёра
    "default": 600,              # 10 минут по умолчанию
}

# Префиксы ключей
KEY_PREFIX = "borodach:"


async def init_cache() -> bool:
    """
    Инициализировать подключение к Redis.
    
    Returns:
        True если подключение успешно, False если Redis недоступен
    """
    global _redis_client
    
    try:
        _redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        
        # Проверяем подключение
        await _redis_client.ping()
        logger.info("redis_connected", url=REDIS_URL.split("@")[-1])  # Скрываем пароль
        return True
        
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        _redis_client = None
        return False


async def close_cache():
    """Закрыть подключение к Redis."""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_closed")


def is_cache_available() -> bool:
    """Проверить, доступен ли кэш."""
    return _redis_client is not None


async def get_cache(key: str) -> Optional[Any]:
    """
    Получить значение из кэша.
    
    Args:
        key: Ключ (без префикса)
    
    Returns:
        Значение или None если не найдено / Redis недоступен
    """
    if not _redis_client:
        return None
    
    try:
        full_key = f"{KEY_PREFIX}{key}"
        value = await _redis_client.get(full_key)
        
        if value:
            logger.debug("cache_hit", key=key)
            return json.loads(value)
        
        logger.debug("cache_miss", key=key)
        return None
        
    except Exception as e:
        logger.warning("cache_get_error", key=key, error=str(e))
        return None


async def set_cache(key: str, value: Any, ttl: int = None) -> bool:
    """
    Сохранить значение в кэш.
    
    Args:
        key: Ключ (без префикса)
        value: Значение (будет сериализовано в JSON)
        ttl: Время жизни в секундах (по умолчанию из CACHE_TTL["default"])
    
    Returns:
        True если успешно, False если ошибка
    """
    if not _redis_client:
        return False
    
    try:
        full_key = f"{KEY_PREFIX}{key}"
        ttl = ttl or CACHE_TTL["default"]
        
        await _redis_client.setex(
            full_key,
            ttl,
            json.dumps(value, ensure_ascii=False, default=str),
        )
        
        logger.debug("cache_set", key=key, ttl=ttl)
        return True
        
    except Exception as e:
        logger.warning("cache_set_error", key=key, error=str(e))
        return False


async def delete_cache(key: str) -> bool:
    """Удалить ключ из кэша."""
    if not _redis_client:
        return False
    
    try:
        full_key = f"{KEY_PREFIX}{key}"
        await _redis_client.delete(full_key)
        logger.debug("cache_delete", key=key)
        return True
        
    except Exception as e:
        logger.warning("cache_delete_error", key=key, error=str(e))
        return False


# === Специализированные функции для кэширования ===

async def cache_network_rating(ratings: List[Dict]) -> bool:
    """
    Закэшировать рейтинг сети.
    
    Args:
        ratings: Список рейтингов салонов
    """
    return await set_cache("network_rating", ratings, CACHE_TTL["network_rating"])


async def get_cached_network_rating() -> Optional[List[Dict]]:
    """Получить рейтинг сети из кэша."""
    return await get_cache("network_rating")


async def cache_companies(companies: List[Dict]) -> bool:
    """
    Закэшировать список салонов.
    
    Args:
        companies: Список салонов из YClients
    """
    return await set_cache("companies", companies, CACHE_TTL["companies"])


async def get_cached_companies() -> Optional[List[Dict]]:
    """Получить список салонов из кэша."""
    return await get_cache("companies")


async def cache_partner_stats(partner_id: int, stats: Dict) -> bool:
    """
    Закэшировать статистику партнёра.
    
    Args:
        partner_id: ID партнёра
        stats: Статистика
    """
    return await set_cache(f"partner_stats:{partner_id}", stats, CACHE_TTL["partner_stats"])


async def get_cached_partner_stats(partner_id: int) -> Optional[Dict]:
    """Получить статистику партнёра из кэша."""
    return await get_cache(f"partner_stats:{partner_id}")


async def invalidate_network_rating():
    """Инвалидировать кэш рейтинга сети."""
    await delete_cache("network_rating")

