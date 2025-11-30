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


async def save_month_to_history(year: int, month: int) -> int:
    """
    Получить данные за указанный месяц из YClients и сохранить в историю.
    Возвращает количество сохранённых записей.
    """
    from database.models import NetworkRatingHistory
    from yclients.client import get_all_companies_metrics
    from admin.analytics import extract_city_from_name
    from sqlalchemy import select
    
    logger.info(f"Fetching data for {year}-{month:02d} from YClients...")
    
    # Проверяем, нет ли уже данных
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(NetworkRatingHistory).where(
                NetworkRatingHistory.year == year,
                NetworkRatingHistory.month == month,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            logger.info(f"History for {year}-{month:02d} already exists, skipping")
            return 0
    
    # Получаем метрики за прошлый месяц НАПРЯМУЮ из YClients
    metrics = await get_all_companies_metrics(year=year, month=month)
    
    if not metrics:
        logger.warning(f"No data for {year}-{month:02d}")
        return 0
    
    # Фильтруем активные и сортируем
    active = [m for m in metrics if m["revenue"] > 0]
    sorted_metrics = sorted(active, key=lambda x: x["revenue"], reverse=True)
    total_companies = len(sorted_metrics)
    
    # Сохраняем в историю
    count = 0
    async with AsyncSessionLocal() as db:
        for i, m in enumerate(sorted_metrics):
            company_name = m["company_name"]
            city = extract_city_from_name(company_name)
            
            history = NetworkRatingHistory(
                yclients_company_id=m["company_id"],
                company_name=company_name,
                city=city,
                revenue=m["revenue"],
                services_revenue=m.get("services_revenue", 0.0),
                products_revenue=m.get("products_revenue", 0.0),
                avg_check=m.get("avg_check", 0.0),
                completed_count=m.get("completed_count", 0),
                repeat_visitors_pct=m.get("repeat_visitors_pct", 0.0),
                new_clients_count=m.get("new_clients_count", 0),
                return_clients_count=m.get("return_clients_count", 0),
                total_clients_count=m.get("total_clients_count", 0),
                client_base_return_pct=m.get("client_base_return_pct", 0.0),
                rank=i + 1,
                total_companies=total_companies,
                year=year,
                month=month,
            )
            db.add(history)
            count += 1
        
        await db.commit()
    
    logger.info(f"Saved {count} records to history for {year}-{month:02d}")
    return count


async def update_network_rating_job():
    """
    Задача обновления рейтинга сети.
    Запрашивает все метрики салонов и сохраняет в БД.
    
    1-го числа месяца: сначала сохраняет историю за ПРОШЛЫЙ месяц,
    затем обновляет текущий рейтинг.
    """
    logger.info("Starting network rating update job...")
    start_time = datetime.now()
    
    try:
        today = datetime.now(ZoneInfo("Europe/Moscow"))
        
        # 1-го числа месяца: сохраняем историю за ПРОШЛЫЙ месяц
        if today.day == 1:
            if today.month == 1:
                prev_year = today.year - 1
                prev_month = 12
            else:
                prev_year = today.year
                prev_month = today.month - 1
            
            # Получаем данные за прошлый месяц из YClients и сохраняем
            saved = await save_month_to_history(prev_year, prev_month)
            logger.info(f"History save complete: {saved} records for {prev_year}-{prev_month:02d}")
        
        # Получаем previous_rank из истории
        from database import get_previous_month_ranks
        
        if today.month == 1:
            prev_year = today.year - 1
            prev_month = 12
        else:
            prev_year = today.year
            prev_month = today.month - 1
        
        async with AsyncSessionLocal() as db:
            previous_ranks = await get_previous_month_ranks(db, prev_year, prev_month)
        
        # Получаем ТЕКУЩИЙ рейтинг (за текущий месяц)
        ranking = await calculate_network_ranking()
        
        if not ranking:
            logger.error("Failed to calculate network ranking - no data received")
            return
        
        from admin.analytics import extract_city_from_name, is_millionnik
        
        # Сохраняем текущий рейтинг с ВСЕМИ метриками
        async with AsyncSessionLocal() as db:
            for company in ranking:
                company_id = company["company_id"]
                company_name = company["company_name"]
                prev_rank = previous_ranks.get(company_id, 0)
                
                city = extract_city_from_name(company_name)
                is_million_city = is_millionnik(city) if city else False
                
                await update_network_rating(
                    db=db,
                    yclients_company_id=company_id,
                    company_name=company_name,
                    revenue=company["revenue"],
                    rank=company["rank"],
                    total_companies=company["total_companies"],
                    avg_check=company.get("avg_check", 0.0),
                    previous_rank=prev_rank,
                    # Расширенные метрики
                    city=city,
                    is_million_city=is_million_city,
                    services_revenue=company.get("services_revenue", 0.0),
                    products_revenue=company.get("products_revenue", 0.0),
                    completed_count=company.get("completed_count", 0),
                    repeat_visitors_pct=company.get("repeat_visitors_pct", 0.0),
                    # Клиентская статистика
                    new_clients_count=company.get("new_clients_count", 0),
                    return_clients_count=company.get("return_clients_count", 0),
                    total_clients_count=company.get("total_clients_count", 0),
                    client_base_return_pct=company.get("client_base_return_pct", 0.0),
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

