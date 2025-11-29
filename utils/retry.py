# Retry logic utilities

import logging
from functools import wraps
from typing import Callable, TypeVar, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)
import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')


# Исключения, при которых стоит повторять запрос
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    ConnectionError,
    TimeoutError,
)


def api_retry(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
    multiplier: float = 2,
):
    """
    Декоратор для автоматических повторов при ошибках API.
    
    Args:
        max_attempts: Максимум попыток (по умолчанию 3)
        min_wait: Минимальная пауза между попытками (сек)
        max_wait: Максимальная пауза между попытками (сек)
        multiplier: Множитель экспоненциального ожидания
    
    Пример использования:
        @api_retry(max_attempts=3)
        async def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_retry(
    func: Callable[..., T],
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 10,
) -> Callable[..., T]:
    """
    Обёртка для применения retry к существующим функциям.
    
    Пример:
        result = await with_retry(api_call, max_attempts=5)(param1, param2)
    """
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await func(*args, **kwargs)
    
    return wrapper

