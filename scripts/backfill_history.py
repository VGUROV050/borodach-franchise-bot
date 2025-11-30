"""
Скрипт для заполнения истории рейтингов за последние 12 месяцев.
Запускает запросы к YClients API за каждый прошлый месяц и сохраняет в БД.

Запуск: python scripts/backfill_history.py
"""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from datetime import datetime, timedelta

from database import AsyncSessionLocal
from database.models import NetworkRatingHistory
from database.crud import get_rating_history
from yclients.client import get_all_companies_metrics, get_chain_companies
from admin.analytics import extract_city_from_name, is_millionnik
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def fetch_and_save_month(year: int, month: int) -> int:
    """
    Получить метрики за указанный месяц и сохранить в историю.
    Возвращает количество сохранённых записей.
    """
    logger.info(f"📅 Загружаем данные за {year}-{month:02d}...")
    
    # Проверяем, нет ли уже данных за этот месяц
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(NetworkRatingHistory).where(
                NetworkRatingHistory.year == year,
                NetworkRatingHistory.month == month,
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            logger.info(f"   ⏭️  Данные за {year}-{month:02d} уже есть, пропускаем")
            return 0
    
    # Получаем метрики за месяц
    metrics = await get_all_companies_metrics(year=year, month=month)
    
    if not metrics:
        logger.warning(f"   ⚠️  Нет данных за {year}-{month:02d}")
        return 0
    
    # Фильтруем салоны с выручкой > 0
    active = [m for m in metrics if m["revenue"] > 0]
    
    # Сортируем по выручке для определения ранга
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
                # Клиентская статистика
                new_clients_count=m.get("new_clients_count", 0),
                return_clients_count=m.get("return_clients_count", 0),
                total_clients_count=m.get("total_clients_count", 0),
                client_base_return_pct=m.get("client_base_return_pct", 0.0),
                # Рейтинг
                rank=i + 1,
                total_companies=total_companies,
                year=year,
                month=month,
            )
            db.add(history)
            count += 1
        
        await db.commit()
    
    logger.info(f"   ✅ Сохранено {count} записей за {year}-{month:02d}")
    return count


async def backfill_12_months(start_months_ago: int = 1, end_months_ago: int = 12):
    """
    Заполнить историю за указанный диапазон месяцев.
    
    Args:
        start_months_ago: С какого месяца начать (1 = прошлый месяц)
        end_months_ago: До какого месяца (12 = год назад)
    """
    logger.info("=" * 60)
    logger.info(f"🚀 ЗАПОЛНЕНИЕ ИСТОРИИ ({start_months_ago}-{end_months_ago} мес. назад)")
    logger.info("=" * 60)
    logger.info("⏱️  Между месяцами пауза 30 сек для защиты API")
    logger.info("")
    
    today = datetime.now()
    total_saved = 0
    
    for months_ago in range(start_months_ago, end_months_ago + 1):
        # Точный расчёт года и месяца
        total_months = today.year * 12 + today.month - months_ago
        year = total_months // 12
        month = total_months % 12
        if month == 0:
            month = 12
            year -= 1
        
        try:
            saved = await fetch_and_save_month(year, month)
            total_saved += saved
            
            # Пауза 30 секунд между месяцами для защиты API
            if saved > 0 and months_ago < end_months_ago:
                logger.info(f"   ⏳ Пауза 30 сек перед следующим месяцем...")
                await asyncio.sleep(30)
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка при загрузке {year}-{month:02d}: {e}")
            # При ошибке ждём дольше
            logger.info(f"   ⏳ Пауза 60 сек после ошибки...")
            await asyncio.sleep(60)
    
    logger.info("=" * 60)
    logger.info(f"🎉 ГОТОВО! Всего сохранено: {total_saved} записей")
    logger.info("=" * 60)


async def show_history_summary():
    """Показать сводку по истории."""
    logger.info("\n📊 СВОДКА ПО ИСТОРИИ:")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                NetworkRatingHistory.year,
                NetworkRatingHistory.month,
            ).distinct().order_by(
                NetworkRatingHistory.year.desc(),
                NetworkRatingHistory.month.desc(),
            )
        )
        months = result.all()
        
        if not months:
            logger.info("   История пуста")
            return
        
        for year, month in months:
            count_result = await db.execute(
                select(NetworkRatingHistory).where(
                    NetworkRatingHistory.year == year,
                    NetworkRatingHistory.month == month,
                )
            )
            count = len(count_result.scalars().all())
            logger.info(f"   📅 {year}-{month:02d}: {count} салонов")


async def main():
    """Главная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Заполнение истории рейтингов')
    parser.add_argument('--start', type=int, default=1, help='Начать с N месяцев назад (default: 1)')
    parser.add_argument('--end', type=int, default=12, help='Закончить N месяцев назад (default: 12)')
    parser.add_argument('--batch', type=int, default=3, help='Обрабатывать по N месяцев за раз (default: 3)')
    
    args = parser.parse_args()
    
    if args.batch and args.batch < (args.end - args.start + 1):
        # Режим батчей
        logger.info(f"🔄 Режим батчей: по {args.batch} месяца за запуск")
        end = min(args.start + args.batch - 1, args.end)
        await backfill_12_months(args.start, end)
        
        if end < args.end:
            logger.info(f"\n💡 Для продолжения запустите:")
            logger.info(f"   python scripts/backfill_history.py --start {end + 1} --end {args.end}")
    else:
        await backfill_12_months(args.start, args.end)
    
    await show_history_summary()


if __name__ == "__main__":
    asyncio.run(main())

