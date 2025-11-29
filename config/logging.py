# Structured logging configuration with structlog

import logging
import sys
from typing import Any

import structlog


def setup_logging(json_logs: bool = False, log_level: str = "INFO"):
    """
    Настройка структурированного логирования.
    
    Args:
        json_logs: Если True, логи выводятся в JSON (для production)
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    """
    
    # Общие процессоры для всех логов
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if json_logs:
        # Production: JSON-формат для удобного парсинга
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: красивый консольный вывод
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    # Настраиваем structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Настраиваем стандартный logging для сторонних библиотек
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=getattr(logging, log_level.upper()),
        stream=sys.stdout,
    )
    
    # Уменьшаем уровень логирования для шумных библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Получить структурированный логгер.
    
    Args:
        name: Имя логгера (обычно __name__)
    
    Returns:
        Структурированный логгер с методами:
        - logger.info("message", key=value, ...)
        - logger.error("message", exc_info=True, ...)
        - logger.bind(user_id=123).info("action")
    
    Пример использования:
        logger = get_logger(__name__)
        logger.info("task_created", task_id=123, user_id=456)
        
        # С контекстом
        log = logger.bind(user_id=456)
        log.info("started")
        log.info("completed")
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


# Хелпер для добавления контекста запроса
def bind_request_context(**kwargs: Any):
    """
    Добавить контекст к логам в текущем запросе.
    
    Пример:
        bind_request_context(user_id=123, action="create_task")
        logger.info("processing")  # Автоматически включит user_id и action
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_request_context():
    """Очистить контекст запроса."""
    structlog.contextvars.clear_contextvars()

