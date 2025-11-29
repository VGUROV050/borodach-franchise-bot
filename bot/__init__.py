# Bot module

from aiogram import Router

from .handlers import router as handlers_router
from .registration import router as registration_router
from .polls import router as polls_router

# Главный роутер, объединяющий все хэндлеры
# ВАЖНО: registration_router первый, чтобы FSM состояния регистрации обрабатывались правильно
main_router = Router()
main_router.include_router(registration_router)
main_router.include_router(handlers_router)
main_router.include_router(polls_router)

__all__ = ["main_router"]
