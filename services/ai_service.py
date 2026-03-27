from __future__ import annotations

import logging

from bot.ai_assistant import get_smart_answer

logger = logging.getLogger(__name__)


async def ask_question(question: str, telegram_id: int, detailed: bool = False) -> str:
    return await get_smart_answer(question, telegram_id, detailed=detailed)
