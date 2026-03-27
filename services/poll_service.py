from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from database import (
    AsyncSessionLocal,
    PollStatus,
    get_all_polls,
    get_poll_by_id,
    save_poll_response,
)

logger = logging.getLogger(__name__)


@dataclass
class PollOptionItem:
    id: int
    text: str
    position: int


@dataclass
class PollItem:
    id: int
    question: str
    is_anonymous: bool
    allows_multiple: bool
    status: str
    options: list[PollOptionItem] = field(default_factory=list)
    created_at: Optional[datetime] = None


async def get_active_polls() -> list[PollItem]:
    async with AsyncSessionLocal() as db:
        polls = await get_all_polls(db, status=PollStatus.SENT)

    return [
        PollItem(
            id=p.id,
            question=p.question,
            is_anonymous=p.is_anonymous,
            allows_multiple=p.allows_multiple,
            status=p.status.value,
            options=[
                PollOptionItem(id=o.id, text=o.text, position=o.position)
                for o in sorted(p.options, key=lambda o: o.position)
            ],
            created_at=p.created_at,
        )
        for p in polls
    ]


async def vote_in_poll(poll_id: int, partner_id: int, option_ids: list[int]) -> bool:
    async with AsyncSessionLocal() as db:
        poll = await get_poll_by_id(db, poll_id)
        if not poll or poll.status != PollStatus.SENT:
            return False

        valid_option_ids = {o.id for o in poll.options}
        if not all(oid in valid_option_ids for oid in option_ids):
            return False

        if not poll.allows_multiple and len(option_ids) > 1:
            return False

        await save_poll_response(db, poll_id, partner_id, option_ids)
        return True
