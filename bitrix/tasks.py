# Bitrix tasks

import logging
from typing import Any

from config.settings import DEPARTMENTS
from .client import call_method, BitrixClientError

logger = logging.getLogger(__name__)

# Кэш этапов Kanban для проектов (group_id -> {stage_id -> stage_name})
_stages_cache: dict[str, dict[str, str]] = {}


async def get_project_stages(group_id: str) -> dict[str, str]:
    """
    Получить этапы Kanban для проекта.
    
    Args:
        group_id: ID проекта/группы в Bitrix
        
    Returns:
        Словарь {stage_id: stage_name}
    """
    # Проверяем кэш
    if group_id in _stages_cache:
        return _stages_cache[group_id]
    
    try:
        params = {"entityId": group_id}
        response = await call_method("task.stages.get", params)
        
        stages_data = response.get("result", {})
        
        # Преобразуем в словарь id -> title
        stages = {}
        for stage_id, stage_info in stages_data.items():
            if isinstance(stage_info, dict):
                stages[str(stage_id)] = stage_info.get("TITLE", f"Этап {stage_id}")
        
        # Сохраняем в кэш
        _stages_cache[group_id] = stages
        logger.info(f"Loaded {len(stages)} stages for group {group_id}")
        
        return stages
        
    except BitrixClientError as e:
        logger.warning(f"Failed to get stages for group {group_id}: {e}")
        return {}


async def create_task(
    group_id: str,
    responsible_id: str,
    department_name: str,
    branch: str,
    description: str,
    telegram_user_id: int,
    telegram_username: str | None,
    telegram_name: str,
) -> int:
    """
    Создать задачу в Bitrix24.
    
    Args:
        group_id: ID проекта/группы в Bitrix
        responsible_id: ID ответственного сотрудника в Bitrix
        department_name: Название отдела для отображения
        branch: Филиал (город/ТЦ/адрес)
        description: Описание задачи от пользователя
        telegram_user_id: ID пользователя в Telegram
        telegram_username: Username в Telegram (может быть None)
        telegram_name: Имя пользователя в Telegram
        
    Returns:
        ID созданной задачи в Bitrix
        
    Raises:
        BitrixClientError: При ошибке создания задачи
    """
    # Формируем username для отображения
    username_display = f"@{telegram_username}" if telegram_username else "нет username"
    
    # Формируем описание задачи
    full_description = f"""🏢 Отдел: {department_name}
📍 Филиал: {branch}

📝 Описание задачи:
{description}

━━━━━━━━━━━━━━━━━━━━━━
👤 Отправитель: {telegram_name} ({username_display})
TG_USER_ID: {telegram_user_id}"""

    params = {
        "fields": {
            "TITLE": f"[{branch}] Задача от франчайзи",
            "DESCRIPTION": full_description,
            "GROUP_ID": group_id,
            "RESPONSIBLE_ID": responsible_id,
            "PRIORITY": "1",  # Средний приоритет
        }
    }
    
    logger.info(f"Creating task for user {telegram_user_id}, dept: {department_name}, branch: {branch}")
    
    response = await call_method("tasks.task.add", params)
    
    task_id = response.get("result", {}).get("task", {}).get("id")
    if not task_id:
        logger.error(f"Unexpected response structure: {response}")
        raise BitrixClientError("Не удалось получить ID задачи из ответа")
    
    logger.info(f"Task created: #{task_id}")
    return int(task_id)


async def get_user_tasks(telegram_user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """
    Получить задачи пользователя по его Telegram ID из всех отделов.
    
    Args:
        telegram_user_id: ID пользователя в Telegram
        limit: Максимальное количество задач
        
    Returns:
        Список задач пользователя с названием этапа Kanban
    """
    # Собираем все group_id из настроек
    group_ids = [
        dept["group_id"] 
        for dept in DEPARTMENTS.values() 
        if dept["group_id"]
    ]
    
    if not group_ids:
        logger.warning("No department group IDs configured")
        return []
    
    all_user_tasks = []
    
    for group_id in group_ids:
        # Получаем этапы для этого проекта
        stages = await get_project_stages(group_id)
        
        params = {
            "filter": {
                "GROUP_ID": group_id,
            },
            "select": ["ID", "TITLE", "STATUS", "STAGE_ID", "CREATED_DATE", "DESCRIPTION", "GROUP_ID"],
            "order": {"CREATED_DATE": "desc"},
            "start": 0,
        }
        
        try:
            response = await call_method("tasks.task.list", params)
            tasks = response.get("result", {}).get("tasks", [])
            
            # Фильтруем по TG_USER_ID в описании
            search_pattern = f"TG_USER_ID: {telegram_user_id}"
            for task in tasks:
                if search_pattern in task.get("description", ""):
                    # Добавляем название этапа
                    stage_id = str(task.get("stageId", ""))
                    task["stage_name"] = stages.get(stage_id, "")
                    all_user_tasks.append(task)
            
        except BitrixClientError as e:
            logger.warning(f"Failed to fetch tasks from group {group_id}: {e}")
            continue
    
    # Сортируем по дате создания (новые первые)
    all_user_tasks.sort(key=lambda t: t.get("createdDate", ""), reverse=True)
    
    logger.info(f"Found {len(all_user_tasks)} tasks for user {telegram_user_id}")
    
    return all_user_tasks[:limit]


def format_task_stage(stage_name: str) -> str:
    """Отформатировать название этапа для отображения."""
    if not stage_name:
        return "📋 Без этапа"
    return f"📋 {stage_name}"
