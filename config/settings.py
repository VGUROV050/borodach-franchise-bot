# Application settings

import os
from dotenv import load_dotenv

# Путь к корню проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Загружаем .env из корня проекта
load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "")

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://borodach_bot:password@localhost:5432/borodach_franchise"
)

# Admin panel
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "change-me-in-production")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# YClients API
YCLIENTS_PARTNER_TOKEN = os.getenv("YCLIENTS_PARTNER_TOKEN", "")
YCLIENTS_USER_TOKEN = os.getenv("YCLIENTS_USER_TOKEN", "")
YCLIENTS_CHAIN_ID = os.getenv("YCLIENTS_CHAIN_ID", "318")  # ID сети салонов

# Redis (для кэширования)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# OpenAI API (для AI-ассистента)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Sentry (мониторинг ошибок)
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Environment (production/development)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# ID проектов/групп в Bitrix24 для каждого отдела
BITRIX_GROUP_ID_DEVELOPMENT = os.getenv("BITRIX_GROUP_ID_DEVELOPMENT", "")  # Отдел Развития
BITRIX_GROUP_ID_MARKETING = os.getenv("BITRIX_GROUP_ID_MARKETING", "")      # Отдел Маркетинга
BITRIX_GROUP_ID_DESIGN = os.getenv("BITRIX_GROUP_ID_DESIGN", "")            # Дизайн

# ID ответственных сотрудников в Bitrix24 для каждого отдела
BITRIX_RESPONSIBLE_DEVELOPMENT = os.getenv("BITRIX_RESPONSIBLE_DEVELOPMENT", "")
BITRIX_RESPONSIBLE_MARKETING = os.getenv("BITRIX_RESPONSIBLE_MARKETING", "")
BITRIX_RESPONSIBLE_DESIGN = os.getenv("BITRIX_RESPONSIBLE_DESIGN", "")

# Маппинг отделов на их Bitrix Group ID и ответственного
DEPARTMENTS = {
    "development": {
        "name": "🚀 Отдел Развития",
        "group_id": BITRIX_GROUP_ID_DEVELOPMENT,
        "responsible_id": BITRIX_RESPONSIBLE_DEVELOPMENT,
    },
    "marketing": {
        "name": "📢 Отдел Маркетинга",
        "group_id": BITRIX_GROUP_ID_MARKETING,
        "responsible_id": BITRIX_RESPONSIBLE_MARKETING,
    },
    "design": {
        "name": "🎨 Дизайн",
        "group_id": BITRIX_GROUP_ID_DESIGN,
        "responsible_id": BITRIX_RESPONSIBLE_DESIGN,
    },
}
