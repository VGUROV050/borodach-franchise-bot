# Bot middleware: rate limiting, logging, etc.

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from config.logging import get_logger, bind_request_context, clear_request_context

logger = get_logger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты сообщений от пользователей.
    
    Защищает от:
    - Спама от одного пользователя
    - Перегрузки бота
    - Случайных множественных нажатий
    """
    
    def __init__(
        self,
        rate_limit: float = 0.5,  # Минимальный интервал между сообщениями (сек)
        throttle_message: str = None,  # Сообщение при троттлинге (None = игнорировать)
    ):
        self.rate_limit = rate_limit
        self.throttle_message = throttle_message
        self._user_last_message: Dict[int, float] = {}
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Применяем только к сообщениям
        if not isinstance(event, Message):
            return await handler(event, data)
        
        user_id = event.from_user.id if event.from_user else None
        
        if user_id:
            now = time.time()
            last_time = self._user_last_message.get(user_id, 0)
            
            # Проверяем интервал
            if now - last_time < self.rate_limit:
                logger.debug(
                    "rate_limit_triggered",
                    user_id=user_id,
                    interval=round(now - last_time, 2),
                )
                
                # Если нужно отправить сообщение о троттлинге
                if self.throttle_message:
                    await event.answer(self.throttle_message)
                
                # Игнорируем сообщение
                return None
            
            # Обновляем время последнего сообщения
            self._user_last_message[user_id] = now
            
            # Периодически чистим старые записи (каждые 100 сообщений)
            if len(self._user_last_message) > 1000:
                cutoff = now - 3600  # Удаляем записи старше часа
                self._user_last_message = {
                    uid: t for uid, t in self._user_last_message.items()
                    if t > cutoff
                }
        
        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования всех входящих сообщений.
    Добавляет контекст пользователя к логам.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Извлекаем информацию о пользователе
        user = None
        chat = None
        
        if isinstance(event, Message):
            user = event.from_user
            chat = event.chat
            message_text = event.text or event.caption or "[media]"
        else:
            message_text = str(type(event).__name__)
        
        # Добавляем контекст к логам
        if user:
            bind_request_context(
                user_id=user.id,
                username=user.username,
                chat_id=chat.id if chat else None,
            )
        
        # Логируем входящее сообщение
        logger.info(
            "incoming_message",
            message_type=type(event).__name__,
            text=message_text[:100] if message_text else None,
        )
        
        try:
            result = await handler(event, data)
            return result
        except Exception as e:
            logger.error(
                "handler_error",
                error=str(e),
                exc_info=True,
            )
            raise
        finally:
            # Очищаем контекст после обработки
            clear_request_context()

