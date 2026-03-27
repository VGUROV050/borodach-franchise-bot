# Statistics service — shared business logic
#
# Extracted from bot/handlers.py `_show_statistics` so that both the
# Telegram bot and the mobile API can reuse the same data-fetching logic.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from database import (
    AsyncSessionLocal,
    get_partner_companies,
    get_network_rating_by_company,
    get_rating_history,
)
from yclients import get_period_revenue

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

PERIOD_LABELS = {
    "today": "Сегодня",
    "yesterday": "Вчера",
    "current_month": "Текущий месяц",
    "prev_month": "Прошлый месяц",
}


@dataclass
class CompanyStats:
    name: str
    yclients_id: Optional[str]
    revenue: float = 0
    completed_count: int = 0
    total_count: int = 0
    rank: int = 0
    total_companies: int = 0
    rank_change: int = 0
    avg_check: float = 0
    error: Optional[str] = None


@dataclass
class PeriodStats:
    period_type: str
    period_label: str
    date_from: str
    date_to: str
    companies: list[CompanyStats] = field(default_factory=list)
    total_revenue: float = 0
    total_completed: int = 0


def _resolve_period(period_type: str) -> tuple[datetime, datetime, str]:
    """Return (date_from, date_to, label) for the given period key."""
    now = datetime.now(MOSCOW_TZ)

    if period_type == "today":
        date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = now
        label = f"Сегодня — {now.strftime('%d.%m.%Y')}"
    elif period_type == "yesterday":
        yesterday = now - timedelta(days=1)
        date_from = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = yesterday.replace(hour=23, minute=59, second=59)
        label = f"Вчера — {yesterday.strftime('%d.%m.%Y')}"
    elif period_type == "prev_month":
        first_day_this_month = now.replace(day=1)
        last_day_prev = first_day_this_month - timedelta(days=1)
        date_from = last_day_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_to = last_day_prev.replace(hour=23, minute=59, second=59)
        label = f"{date_from.strftime('%d.%m')} — {date_to.strftime('%d.%m.%Y')}"
    else:
        date_from = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_to = now
        label = f"{date_from.strftime('%d.%m')} — {date_to.strftime('%d.%m.%Y')}"
        period_type = "current_month"

    return date_from, date_to, label


async def get_statistics(partner_id: int, period_type: str = "current_month") -> Optional[PeriodStats]:
    """
    Fetch statistics for all companies linked to *partner_id*.

    Returns a plain dataclass — the caller (bot or API) decides how to render it.
    """
    date_from, date_to, label = _resolve_period(period_type)

    async with AsyncSessionLocal() as db:
        companies = await get_partner_companies(db, partner_id)

    if not companies:
        return None

    result = PeriodStats(
        period_type=period_type,
        period_label=label,
        date_from=date_from.strftime("%Y-%m-%d"),
        date_to=date_to.strftime("%Y-%m-%d"),
    )

    for company in companies:
        cs = CompanyStats(name=company.name, yclients_id=company.yclients_id)

        if not company.yclients_id:
            cs.error = "YClients ID не указан"
            result.companies.append(cs)
            continue

        ycl_result = await get_period_revenue(
            company.yclients_id,
            date_from.strftime("%Y-%m-%d"),
            date_to.strftime("%Y-%m-%d"),
        )

        if ycl_result.get("success"):
            cs.revenue = ycl_result.get("revenue", 0)
            cs.completed_count = ycl_result.get("completed_count", 0)
            cs.total_count = ycl_result.get("total_count", 0)
            result.total_revenue += cs.revenue
            result.total_completed += cs.completed_count

            if period_type in ("current_month", "prev_month"):
                await _enrich_with_rating(cs, company.yclients_id, period_type, date_from)
        else:
            cs.error = ycl_result.get("error", "Ошибка загрузки")

        result.companies.append(cs)

    return result


async def _enrich_with_rating(
    cs: CompanyStats,
    yclients_id: str,
    period_type: str,
    date_from: datetime,
) -> None:
    """Attach ranking info to a CompanyStats object."""
    async with AsyncSessionLocal() as db:
        if period_type == "current_month":
            rating = await get_network_rating_by_company(db, yclients_id)
            if rating and rating.rank > 0:
                cs.rank = rating.rank
                cs.total_companies = rating.total_companies
                cs.avg_check = rating.avg_check or 0
                if rating.previous_rank and rating.previous_rank > 0:
                    cs.rank_change = rating.previous_rank - rating.rank
        else:
            history = await get_rating_history(db, date_from.year, date_from.month)
            entry = next((h for h in history if h.yclients_company_id == yclients_id), None)
            if entry and entry.rank > 0:
                cs.rank = entry.rank
                cs.total_companies = len(history)
                cs.avg_check = entry.avg_check or 0
