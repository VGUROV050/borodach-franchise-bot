# Main entry point for Borodach Franchise Bot

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import TELEGRAM_BOT_TOKEN
from bot import main_router
from database import init_db, close_db
from scheduler import start_scheduler, stop_scheduler, update_network_rating_now


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")

    # Инициализация БД
    logger.info("Connecting to database...")
    await init_db()
    
    # Запускаем планировщик для обновления рейтинга сети
    logger.info("Starting scheduler...")
    start_scheduler()
    
    # Первоначальная загрузка рейтинга (если БД пустая)
    # Запускаем в фоне чтобы не блокировать старт бота
    asyncio.create_task(initial_rating_load())

    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    # MemoryStorage для FSM (состояния сбросятся при перезапуске)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(main_router)

    try:
        logger.info("Starting bot polling...")
        # Явно указываем типы обновлений, включая poll_answer
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query", 
                "poll_answer",  # Для получения ответов на опросы
            ],
        )
    finally:
        # Останавливаем планировщик
        stop_scheduler()
        # Закрываем соединение с БД при остановке
        await close_db()


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
    asyncio.run(main())
