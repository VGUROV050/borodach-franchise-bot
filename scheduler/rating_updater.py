# Network rating updater scheduler

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import AsyncSessionLocal, update_network_rating
from yclients import calculate_network_ranking

logger = logging.getLogger(__name__)

# Глобальная переменная для планировщика
_scheduler: AsyncIOScheduler = None


async def update_network_rating_job():
    """
    Задача обновления рейтинга сети.
    Запрашивает выручку всех салонов и сохраняет рейтинг в БД.
    """
    logger.info("Starting network rating update job...")
    start_time = datetime.now()
    
    try:
        # Получаем рейтинг всех салонов
        ranking = await calculate_network_ranking()
        
        if not ranking:
            logger.error("Failed to calculate network ranking - no data received")
            return
        
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
                )
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Network rating update completed! "
            f"Updated {len(ranking)} companies in {duration:.1f} seconds"
        )
        
    except Exception as e:
        logger.error(f"Error in network rating update job: {e}", exc_info=True)


async def update_network_rating_now():
    """
    Запустить обновление рейтинга прямо сейчас (вручную).
    Полезно для первоначальной загрузки или отладки.
    """
    logger.info("Manual network rating update requested")
    await update_network_rating_job()


def start_scheduler():
    """
    Запустить планировщик задач.
    Обновление рейтинга запланировано на 1:00 МСК каждый день.
    """
    global _scheduler
    
    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    _scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Moscow"))
    
    # Запускаем обновление рейтинга в 1:00 МСК каждый день
    _scheduler.add_job(
        update_network_rating_job,
        CronTrigger(hour=1, minute=0, timezone=ZoneInfo("Europe/Moscow")),
        id="network_rating_update",
        name="Update network rating",
        replace_existing=True,
    )
    
    _scheduler.start()
    
    logger.info("Scheduler started. Network rating will update daily at 1:00 MSK")
    
    # Логируем следующий запуск
    job = _scheduler.get_job("network_rating_update")
    if job:
        next_run = job.next_run_time
        logger.info(f"Next rating update scheduled for: {next_run}")


def stop_scheduler():
    """Остановить планировщик."""
    global _scheduler
    
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")

