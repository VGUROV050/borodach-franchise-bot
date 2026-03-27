# Mobile API — network rating routes

from enum import Enum

from fastapi import APIRouter, Depends, HTTPException

from mobile_api.deps import get_current_partner_id
from mobile_api.schemas import RatingOut, RatingEntryOut
from services.rating_service import get_network_rating

router = APIRouter()


class RatingPeriod(str, Enum):
    current = "current"
    previous = "previous"


@router.get("/rating/{period}", response_model=RatingOut)
async def get_rating(
    period: RatingPeriod,
    partner_id: int = Depends(get_current_partner_id),
):
    data = await get_network_rating(partner_id, period.value)
    if data is None:
        raise HTTPException(status_code=404, detail="Rating data not available")
    return RatingOut(
        period_label=data.period_label,
        total_companies=data.total_companies,
        partner_ranks=data.partner_ranks,
        entries=[
            RatingEntryOut(
                rank=e.rank,
                yclients_company_id=e.yclients_company_id,
                company_name=e.company_name,
                location=e.location,
                region=e.region,
                revenue=e.revenue,
                avg_check=e.avg_check,
                rank_change=e.rank_change,
                is_partner=e.is_partner,
            )
            for e in data.entries
        ],
    )
