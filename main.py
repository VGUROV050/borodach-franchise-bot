# Main entry point for Borodach Franchise Bot

import asyncio
import signal
import sys
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import TELEGRAM_BOT_TOKEN
from config.logging import setup_logging, get_logger
from bot import main_router
from database import init_db, close_db
from cache import init_cache, close_cache
from scheduler import start_scheduler, stop_scheduler, update_network_rating_now

# Инициализируем структурированное логирование
setup_logging(json_logs=False, log_level="INFO")

logger = get_logger(__name__)

# Глобальные переменные для graceful shutdown
_bot: Optional[Bot] = None
_dp: Optional[Dispatcher] = None
_shutdown_event: Optional[asyncio.Event] = None


async def shutdown(sig: Optional[signal.Signals] = None):
    """Graceful shutdown: корректное завершение всех компонентов."""
    if sig:
        logger.info(f"Received signal {sig.name}, shutting down...")
    else:
        logger.info("Shutting down...")
    
    # 1. Останавливаем polling (если dispatcher активен)
    if _dp:
        logger.info("Stopping dispatcher...")
        await _dp.stop_polling()
    
    # 2. Закрываем сессию бота
    if _bot:
        logger.info("Closing bot session...")
        await _bot.session.close()
    
    # 3. Останавливаем планировщик (ждём завершения текущих задач)
    logger.info("Stopping scheduler...")
    stop_scheduler()
    
    # 4. Закрываем Redis
    logger.info("Closing Redis cache...")
    await close_cache()
    
    # 5. Закрываем соединения с БД
    logger.info("Closing database connections...")
    await close_db()
    
    logger.info("Shutdown complete.")
    
    # Сигнализируем о завершении
    if _shutdown_event:
        _shutdown_event.set()


def handle_signal(sig: signal.Signals, loop: asyncio.AbstractEventLoop):
    """Обработчик сигналов SIGINT/SIGTERM."""
    logger.info(f"Signal {sig.name} received")
    loop.create_task(shutdown(sig))


async def main():
    global _bot, _dp, _shutdown_event
    
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")

    # Создаём событие для graceful shutdown
    _shutdown_event = asyncio.Event()
    
    # Регистрируем обработчики сигналов
    loop = asyncio.get_running_loop()
    
    # На Unix-системах обрабатываем SIGINT и SIGTERM
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda s=sig: handle_signal(s, loop)
            )
    
    # Инициализация БД
    logger.info("Connecting to database...")
    await init_db()
    
    # Инициализация Redis кэша (опционально - работает и без него)
    logger.info("Connecting to Redis cache...")
    cache_available = await init_cache()
    if not cache_available:
        logger.warning("Redis unavailable, running without cache")
    
    # Запускаем планировщик для обновления рейтинга сети
    logger.info("Starting scheduler...")
    start_scheduler()
    
    # Первоначальная загрузка рейтинга (если БД пустая)
    # Запускаем в фоне чтобы не блокировать старт бота
    asyncio.create_task(initial_rating_load())

    _bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    
    # MemoryStorage для FSM (состояния сбросятся при перезапуске)
    _dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем middleware
    from bot.middleware import RateLimitMiddleware, LoggingMiddleware
    _dp.message.middleware(RateLimitMiddleware(rate_limit=0.5))  # 2 сообщения/сек макс
    _dp.message.middleware(LoggingMiddleware())
    
    _dp.include_router(main_router)

    try:
        logger.info("Starting bot polling...")
        # Явно указываем типы обновлений, включая poll_answer
        await _dp.start_polling(
            _bot,
            allowed_updates=[
                "message",
                "callback_query", 
                "poll_answer",  # Для получения ответов на опросы
            ],
        )
    except asyncio.CancelledError:
        logger.info("Polling cancelled")
    finally:
        # Graceful shutdown если не был вызван через сигнал
        if not _shutdown_event.is_set():
            await shutdown()


async def initial_rating_load():
    """Загрузить рейтинг при старте если БД пустая."""
    try:
        from database import AsyncSessionLocal, get_all_network_ratings
        
        async with AsyncSessionLocal() as db:
            ratings = await get_all_network_ratings(db)
        
        if not ratings:
            logger.info("Network rating is empty, loading initial data...")
            await update_network_rating_now()
        else:
            logger.info(f"Network rating already has {len(ratings)} entries")
            
    except Exception as e:
        logger.error(f"Error in initial rating load: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
