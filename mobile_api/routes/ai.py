from fastapi import APIRouter, Depends, HTTPException

from database import AsyncSessionLocal, get_partner_by_id
from mobile_api.deps import get_current_partner_id
from mobile_api.schemas import AiAskIn, AiAskOut
from services.ai_service import ask_question

router = APIRouter()


@router.post("/ai/ask", response_model=AiAskOut)
async def ai_ask(
    body: AiAskIn,
    partner_id: int = Depends(get_current_partner_id),
):
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_id(db, partner_id)
    if not partner or not partner.telegram_id:
        raise HTTPException(status_code=404, detail="Partner not found")

    answer = await ask_question(body.question, partner.telegram_id, detailed=body.detailed)
    return AiAskOut(answer=answer)
