# Database connection

import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

# Создаём асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Поставь True для отладки SQL-запросов
    pool_pre_ping=True,
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Инициализация подключения к БД (проверка соединения)."""
    try:
        async with engine.begin() as conn:
            # Простая проверка подключения
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_db() -> None:
    """Закрытие подключения к БД."""
    await engine.dispose()
    logger.info("Database connection closed")

