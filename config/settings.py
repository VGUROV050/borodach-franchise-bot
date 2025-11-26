# Application settings

import os
from dotenv import load_dotenv

# Путь к корню проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Загружаем .env из корня проекта
load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "")

# ID проектов/групп в Bitrix24 для каждого отдела
BITRIX_GROUP_ID_DEVELOPMENT = os.getenv("BITRIX_GROUP_ID_DEVELOPMENT", "")  # Отдел Развития
BITRIX_GROUP_ID_MARKETING = os.getenv("BITRIX_GROUP_ID_MARKETING", "")      # Отдел Маркетинга
BITRIX_GROUP_ID_DESIGN = os.getenv("BITRIX_GROUP_ID_DESIGN", "")            # Дизайн

# Маппинг отделов на их Bitrix Group ID
DEPARTMENTS = {
    "development": {
        "name": "🚀 Отдел Развития",
        "group_id": BITRIX_GROUP_ID_DEVELOPMENT,
    },
    "marketing": {
        "name": "📢 Отдел Маркетинга",
        "group_id": BITRIX_GROUP_ID_MARKETING,
    },
    "design": {
        "name": "🎨 Дизайн",
        "group_id": BITRIX_GROUP_ID_DESIGN,
    },
}
