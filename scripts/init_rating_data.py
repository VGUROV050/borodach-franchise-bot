#!/usr/bin/env python3
"""
Скрипт для инициализации данных рейтинга сети.
Загружает текущий рейтинг и сохраняет историю за предыдущие месяцы.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from database import AsyncSessionLocal, update_network_rating, NetworkRatingHistory
from yclients import calculate_network_ranking
from sqlalchemy import select

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_current_rating():
    """Загрузить текущий рейтинг из YClients."""
    logger.info("Загружаем текущий рейтинг из YClients...")
    
    ranking = await calculate_network_ranking()
    
    if not ranking:
        logger.error("Не удалось получить данные из YClients")
        return None
    
    logger.info(f"Получено {len(ranking)} салонов")
    
    # Сохраняем в БД
    async with AsyncSessionLocal() as db:
        for company in ranking:
            await update_network_rating(
                db=db,
                yclients_company_id=company["company_id"],
                company_name=company["company_name"],
                revenue=company["revenue"],
                rank=company["rank"],
                total_companies=company["total_companies"],
                avg_check=company.get("avg_check", 0.0),
                previous_rank=0,  # Нет истории пока
            )
    
    logger.info("Текущий рейтинг сохранён в БД")
    return ranking


def get_prev_month(year: int, month: int) -> tuple[int, int]:
    """Получить предыдущий месяц."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


async def save_history_for_month(ranking: list, year: int, month: int):
    """
    Сохранить рейтинг как историю за указанный месяц.
    """
    logger.info(f"Сохраняем историю за {year}-{month:02d}...")
    
    async with AsyncSessionLocal() as db:
        # Проверяем, есть ли уже данные за этот период
        existing = await db.execute(
            select(NetworkRatingHistory).where(
                NetworkRatingHistory.year == year,
                NetworkRatingHistory.month == month
            ).limit(1)
        )
        if existing.scalar():
            logger.info(f"История за {year}-{month:02d} уже существует, пропускаем")
            return False
        
        # Сохраняем историю
        total_companies = ranking[0]["total_companies"] if ranking else 0
        for company in ranking:
            history = NetworkRatingHistory(
                yclients_company_id=company["company_id"],
                company_name=company["company_name"],
                revenue=company["revenue"],
                avg_check=company.get("avg_check", 0.0),
                rank=company["rank"],
                total_companies=total_companies,
                year=year,
                month=month,
            )
            db.add(history)
        
        await db.commit()
    
    logger.info(f"История за {year}-{month:02d} сохранена ({len(ranking)} записей)")
    return True


async def save_history_for_two_months(ranking: list):
    """
    Сохранить текущий рейтинг как историю за 2 предыдущих месяца.
    Это нужно для:
    - Вкладка "Прошлый месяц": октябрь vs сентябрь
    - Вкладка "Текущий месяц": ноябрь vs октябрь
    """
    today = datetime.now(ZoneInfo("Europe/Moscow"))
    
    # Прошлый месяц (октябрь)
    prev_year, prev_month = get_prev_month(today.year, today.month)
    
    # Позапрошлый месяц (сентябрь)
    prev_prev_year, prev_prev_month = get_prev_month(prev_year, prev_month)
    
    # Сохраняем историю за оба месяца
    await save_history_for_month(ranking, prev_year, prev_month)
    await save_history_for_month(ranking, prev_prev_year, prev_prev_month)


async def update_current_with_previous_ranks():
    """Обновить текущий рейтинг с previous_rank из истории."""
    today = datetime.now(ZoneInfo("Europe/Moscow"))
    
    # Определяем прошлый месяц
    if today.month == 1:
        prev_year = today.year - 1
        prev_month = 12
    else:
        prev_year = today.year
        prev_month = today.month - 1
    
    logger.info("Обновляем previous_rank в текущем рейтинге...")
    
    async with AsyncSessionLocal() as db:
        # Получаем ранги из истории
        history = await db.execute(
            select(NetworkRatingHistory).where(
                NetworkRatingHistory.year == prev_year,
                NetworkRatingHistory.month == prev_month
            )
        )
        history_records = history.scalars().all()
        
        previous_ranks = {
            h.yclients_company_id: h.rank 
            for h in history_records
        }
        
        # Обновляем текущий рейтинг
        from database import NetworkRating
        current = await db.execute(select(NetworkRating))
        current_records = current.scalars().all()
        
        updated = 0
        for record in current_records:
            prev_rank = previous_ranks.get(record.yclients_company_id, 0)
            if record.previous_rank != prev_rank:
                record.previous_rank = prev_rank
                updated += 1
        
        await db.commit()
    
    logger.info(f"Обновлено {updated} записей с previous_rank")


async def main():
    """Главная функция инициализации."""
    logger.info("=" * 50)
    logger.info("Инициализация данных рейтинга сети")
    logger.info("=" * 50)
    
    # 1. Загружаем текущий рейтинг
    ranking = await load_current_rating()
    
    if not ranking:
        logger.error("Не удалось загрузить рейтинг")
        return
    
    # 2. Сохраняем как историю за 2 предыдущих месяца (октябрь и сентябрь)
    # Это позволит сравнивать:
    # - Октябрь vs Сентябрь (вкладка "Прошлый месяц")
    # - Ноябрь vs Октябрь (вкладка "Текущий месяц")
    await save_history_for_two_months(ranking)
    
    # 3. Обновляем текущий рейтинг с previous_rank
    await update_current_with_previous_ranks()
    
    logger.info("=" * 50)
    logger.info("Инициализация завершена!")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

