# Application settings

import os
from dotenv import load_dotenv

# Путь к корню проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Загружаем .env из корня проекта
load_dotenv(os.path.join(BASE_DIR, ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BITRIX_WEBHOOK_URL = os.getenv("BITRIX_WEBHOOK_URL", "")
BITRIX_GROUP_ID_IT = os.getenv("BITRIX_GROUP_ID_IT", "")

# На будущее можно добавлять сюда другие настройки, например:
# ENV = os.getenv("ENV", "prod")
