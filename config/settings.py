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
