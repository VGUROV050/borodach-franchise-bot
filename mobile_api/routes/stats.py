# Mobile API — statistics routes

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException

from mobile_api.deps import get_current_partner_id
from mobile_api.schemas import PeriodStatsOut, CompanyStatsOut
from services.stats_service import get_statistics

router = APIRouter()


class Period(str, Enum):
    today = "today"
    yesterday = "yesterday"
    current_month = "current_month"
    prev_month = "prev_month"


@router.get("/stats/{period}", response_model=PeriodStatsOut)
async def get_stats(
    period: Period,
    partner_id: int = Depends(get_current_partner_id),
):
    result = await get_statistics(partner_id, period.value)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No companies linked to this partner",
        )
    return PeriodStatsOut(
        period_type=result.period_type,
        period_label=result.period_label,
        date_from=result.date_from,
        date_to=result.date_to,
        total_revenue=result.total_revenue,
        total_completed=result.total_completed,
        companies=[
            CompanyStatsOut(
                name=c.name,
                yclients_id=c.yclients_id,
                revenue=c.revenue,
                completed_count=c.completed_count,
                total_count=c.total_count,
                rank=c.rank,
                total_companies=c.total_companies,
                rank_change=c.rank_change,
                avg_check=c.avg_check,
                error=c.error,
            )
            for c in result.companies
        ],
    )
