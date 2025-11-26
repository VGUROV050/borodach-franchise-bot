# Main entry point for Borodach Franchise Bot

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config.settings import TELEGRAM_BOT_TOKEN
from bot import main_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")

    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.include_router(main_router)

    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
