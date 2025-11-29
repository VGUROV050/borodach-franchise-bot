# Bot poll handlers
# Обработка ответов на голосования

import logging

from aiogram import Router, F
from aiogram.types import PollAnswer

from database import AsyncSessionLocal, get_partner_by_telegram_id, save_poll_response
from database.models import PollMessage

router = Router()
logger = logging.getLogger(__name__)


@router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer) -> None:
    """
    Обработать ответ пользователя на голосование.
    
    Telegram отправляет PollAnswer когда пользователь голосует или меняет голос.
    poll_answer содержит:
    - poll_id: ID опроса в Telegram
    - user: пользователь, который проголосовал
    - option_ids: список индексов выбранных вариантов (0-based)
    """
    telegram_user_id = poll_answer.user.id
    telegram_poll_id = poll_answer.poll_id
    selected_option_indices = poll_answer.option_ids
    
    logger.info(
        f"Poll answer received: user={telegram_user_id}, "
        f"poll={telegram_poll_id}, options={selected_option_indices}"
    )
    
    async with AsyncSessionLocal() as db:
        # Находим партнёра по Telegram ID
        partner = await get_partner_by_telegram_id(db, telegram_user_id)
        
        if not partner:
            logger.warning(f"Poll answer from unknown user: {telegram_user_id}")
            return
        
        # Находим наше голосование по telegram_poll_id
        from sqlalchemy import select
        
        result = await db.execute(
            select(PollMessage).where(
                PollMessage.telegram_poll_id == telegram_poll_id,
                PollMessage.partner_id == partner.id,
            )
        )
        poll_message = result.scalar_one_or_none()
        
        if not poll_message:
            logger.warning(
                f"Poll message not found: poll_id={telegram_poll_id}, "
                f"partner_id={partner.id}"
            )
            return
        
        poll_id = poll_message.poll_id
        
        # Получаем опции голосования чтобы сопоставить индексы с ID
        from database.models import PollOption
        
        options_result = await db.execute(
            select(PollOption)
            .where(PollOption.poll_id == poll_id)
            .order_by(PollOption.position)
        )
        options = list(options_result.scalars().all())
        
        # Преобразуем индексы в ID опций
        selected_option_ids = []
        for idx in selected_option_indices:
            if 0 <= idx < len(options):
                selected_option_ids.append(options[idx].id)
        
        if not selected_option_ids:
            logger.warning(f"No valid options selected for poll {poll_id}")
            return
        
        # Сохраняем ответ
        await save_poll_response(
            db,
            poll_id=poll_id,
            partner_id=partner.id,
            option_ids=selected_option_ids,
        )
        
        logger.info(
            f"Poll response saved: poll={poll_id}, partner={partner.id}, "
            f"options={selected_option_ids}"
        )

