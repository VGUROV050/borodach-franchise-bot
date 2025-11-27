# Admin panel FastAPI application

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.settings import BASE_DIR
from database import init_db, close_db

from .routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: startup and shutdown."""
    logger.info("Starting admin panel...")
    await init_db()
    yield
    await close_db()
    logger.info("Admin panel stopped")


app = FastAPI(
    title="Borodach Admin",
    description="Админ-панель для управления партнёрами",
    version="1.0.0",
    lifespan=lifespan,
)

# Подключаем роуты
app.include_router(router)

# Настраиваем шаблоны
templates = Jinja2Templates(directory=f"{BASE_DIR}/admin/templates")

