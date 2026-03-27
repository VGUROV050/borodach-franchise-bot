from fastapi import APIRouter, Depends, HTTPException

from mobile_api.deps import get_current_partner_id
from mobile_api.schemas import PollOut, PollOptionOut, PollVoteIn, PollVoteOut
from services.poll_service import get_active_polls, vote_in_poll

router = APIRouter()


@router.get("/polls", response_model=list[PollOut])
async def list_polls():
    polls = await get_active_polls()
    return [
        PollOut(
            id=p.id,
            question=p.question,
            is_anonymous=p.is_anonymous,
            allows_multiple=p.allows_multiple,
            status=p.status,
            options=[
                PollOptionOut(id=o.id, text=o.text, position=o.position)
                for o in p.options
            ],
            created_at=p.created_at,
        )
        for p in polls
    ]


@router.post("/polls/{poll_id}/vote", response_model=PollVoteOut)
async def vote(
    poll_id: int,
    body: PollVoteIn,
    partner_id: int = Depends(get_current_partner_id),
):
    if not body.option_ids:
        raise HTTPException(status_code=400, detail="No options selected")

    success = await vote_in_poll(poll_id, partner_id, body.option_ids)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid poll or options")

    return PollVoteOut(success=True)
