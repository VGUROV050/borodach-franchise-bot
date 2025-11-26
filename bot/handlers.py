# Bot handlers

from aiogram import Router, types
from aiogram.filters import CommandStart

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Это бот для франчайзи BORODACH.\n"
        "Пока я умею только здороваться, но скоро буду создавать задачи в УК 💈"
    )