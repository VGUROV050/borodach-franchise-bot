# Mobile API — FastAPI application
#
# Separate process from the admin panel and Telegram bot.
# Serves JSON endpoints for the React Native mobile app.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, close_db

from .routes import account, stats, rating, health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting mobile API...")
    await init_db()
    yield
    await close_db()
    logger.info("Mobile API stopped")


app = FastAPI(
    title="Borodach Mobile API",
    description="REST API for BORODACH franchise partner mobile app",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(account.router, prefix="/api/v1", tags=["account"])
app.include_router(stats.router, prefix="/api/v1", tags=["statistics"])
app.include_router(rating.router, prefix="/api/v1", tags=["rating"])
