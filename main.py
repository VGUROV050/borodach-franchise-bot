# Main entry point for Borodach Franchise Bot

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import TELEGRAM_BOT_TOKEN
from bot import main_router
from database import init_db, close_db


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

    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    # MemoryStorage для FSM (состояния сбросятся при перезапуске)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(main_router)

    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        # Закрываем соединение с БД при остановке
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
