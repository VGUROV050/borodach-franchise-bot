# Network rating service — shared business logic
#
# Extracted from bot/handlers.py `_show_rating` so that both the
# Telegram bot and the mobile API can reuse the same data-fetching logic.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select

from database import (
    AsyncSessionLocal,
    get_partner_companies,
    get_all_network_ratings,
    get_rating_history,
    get_previous_month_ranks,
)
from database.models import YClientsCompany

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


@dataclass
class RatingEntry:
    rank: int
    yclients_company_id: str
    company_name: str
    location: str
    region: Optional[str]
    revenue: float
    avg_check: float
    rank_change: int
    is_partner: bool


@dataclass
class RatingData:
    period_label: str
    total_companies: int
    entries: list[RatingEntry] = field(default_factory=list)
    partner_ranks: list[int] = field(default_factory=list)


def _format_location(city: Optional[str], region: Optional[str]) -> str:
    if not city and not region:
        return "—"
    city_lower = (city or "").lower()
    if "москва" in city_lower or "moscow" in city_lower:
        return "Москва"
    if "санкт-петербург" in city_lower or "петербург" in city_lower or "спб" in city_lower:
        return "Санкт-Петербург"
    if region:
        return region
    return city or "—"


async def get_network_rating(partner_id: int, period: str = "current") -> Optional[RatingData]:
    """
    Build the full network rating table for the given period.

    Returns a plain dataclass with all entries — the caller decides
    how many rows to show and how to render them.
    """
    is_current = period == "current"
    now = datetime.now(MOSCOW_TZ)

    async with AsyncSessionLocal() as db:
        partner_companies = await get_partner_companies(db, partner_id)
        partner_yclients_ids = {c.yclients_id for c in partner_companies}
        partner_names = {c.yclients_id: c.name for c in partner_companies}

        result = await db.execute(select(YClientsCompany))
        all_yclients = {c.yclients_id: c for c in result.scalars().all()}

        if is_current:
            all_ratings = await get_all_network_ratings(db)
            period_label = f"{MONTH_NAMES[now.month]} {now.year}"
            prev_year, prev_month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
            prev_ranks = await get_previous_month_ranks(db, prev_year, prev_month)
        else:
            target_year, target_month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
            all_ratings = await get_rating_history(db, target_year, target_month)
            period_label = f"{MONTH_NAMES[target_month]} {target_year}"
            py, pm = (target_year - 1, 12) if target_month == 1 else (target_year, target_month - 1)
            prev_ranks = await get_previous_month_ranks(db, py, pm)

    if not all_ratings:
        return None

    filtered = [
        r for r in all_ratings
        if r.revenue > 0 and "закрыт" not in (r.company_name or "").lower()
    ]
    sorted_ratings = sorted(filtered, key=lambda x: x.revenue or 0, reverse=True)
    total = len(sorted_ratings)

    data = RatingData(period_label=period_label, total_companies=total)

    for idx, r in enumerate(sorted_ratings):
        rank = idx + 1
        yid = r.yclients_company_id
        is_partner = yid in partner_yclients_ids

        prev_rank = prev_ranks.get(yid)
        rank_change = (prev_rank - rank) if prev_rank and prev_rank > 0 else 0

        yc = all_yclients.get(yid)
        region = yc.region if yc else None
        location = _format_location(r.city, region)
        display_name = partner_names.get(yid, location) if is_partner else location

        entry = RatingEntry(
            rank=rank,
            yclients_company_id=yid,
            company_name=display_name,
            location=location,
            region=region,
            revenue=r.revenue or 0,
            avg_check=r.avg_check or 0,
            rank_change=rank_change,
            is_partner=is_partner,
        )
        data.entries.append(entry)

        if is_partner:
            data.partner_ranks.append(rank)

    return data
