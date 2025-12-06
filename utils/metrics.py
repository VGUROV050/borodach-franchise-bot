# Prometheus metrics for monitoring

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST

# ═══════════════════════════════════════════════════════════════════
# Counters - счётчики событий
# ═══════════════════════════════════════════════════════════════════

# Телеграм сообщения
telegram_messages_total = Counter(
    'telegram_messages_total',
    'Total Telegram messages received',
    ['message_type']  # text, command, callback
)

# API запросы
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['service', 'endpoint', 'status']  # yclients/bitrix, endpoint, success/error
)

# Bitrix задачи
bitrix_tasks_created = Counter(
    'bitrix_tasks_created_total',
    'Total Bitrix tasks created',
    ['department']  # development, marketing, design
)

# AI-ассистент
ai_assistant_requests = Counter(
    'ai_assistant_requests_total',
    'Total AI assistant requests',
    ['status']  # success, error, no_context
)

# База знаний
knowledge_base_searches = Counter(
    'knowledge_base_searches_total',
    'Total knowledge base searches',
    ['result']  # found, not_found
)

# Ошибки
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['type', 'module']  # api_error/db_error, module name
)

# ═══════════════════════════════════════════════════════════════════
# Histograms - распределение времени
# ═══════════════════════════════════════════════════════════════════

# Время обработки сообщений
message_processing_duration = Histogram(
    'message_processing_seconds',
    'Time spent processing messages',
    ['handler'],  # handler name
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Время API запросов
api_request_duration = Histogram(
    'api_request_seconds',
    'Time spent on API requests',
    ['service'],  # yclients, bitrix, openai
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# Время запросов к БД
db_query_duration = Histogram(
    'db_query_seconds',
    'Time spent on database queries',
    ['operation'],  # select, insert, update
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# ═══════════════════════════════════════════════════════════════════
# Gauges - текущие значения
# ═══════════════════════════════════════════════════════════════════

# Активные пользователи
active_users = Gauge(
    'active_users',
    'Number of active users in last 24h'
)

# Партнёры
partners_total = Gauge(
    'partners_total',
    'Total partners',
    ['status']  # pending, approved, rejected
)

# База знаний
knowledge_base_chunks = Gauge(
    'knowledge_base_chunks_total',
    'Total chunks in knowledge base'
)

knowledge_base_lessons = Gauge(
    'knowledge_base_lessons_total',
    'Total lessons in knowledge base'
)

# ═══════════════════════════════════════════════════════════════════
# Info - метаданные
# ═══════════════════════════════════════════════════════════════════

app_info = Info(
    'borodach_bot',
    'Application information'
)


def init_app_info(version: str = "1.0.0"):
    """Инициализировать информацию о приложении."""
    app_info.info({
        'version': version,
        'name': 'borodach-franchise-bot',
    })


def get_metrics():
    """Получить все метрики в формате Prometheus."""
    return generate_latest()


def get_metrics_content_type():
    """Получить Content-Type для метрик."""
    return CONTENT_TYPE_LATEST

