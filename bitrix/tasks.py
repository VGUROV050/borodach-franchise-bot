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
    if group_id in _stages_cache:
        return _stages_cache[group_id]
    
    try:
        params = {"entityId": group_id}
        response = await call_method("task.stages.get", params)
        
        stages_data = response.get("result", {})
        
        stages = {}
        for stage_id, stage_info in stages_data.items():
            if isinstance(stage_info, dict):
                stages[str(stage_id)] = stage_info.get("TITLE", f"Этап {stage_id}")
        
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
    title: str,
    description: str,
    telegram_user_id: int,
    telegram_username: str | None,
    telegram_name: str,
    files: list[dict[str, Any]] | None = None,
) -> int:
    """
    Создать задачу в Bitrix24.
    
    Args:
        group_id: ID проекта/группы в Bitrix
        responsible_id: ID ответственного сотрудника в Bitrix
        department_name: Название отдела для отображения
        branch: Филиал (город/ТЦ/адрес)
        title: Заголовок задачи от пользователя
        description: Описание задачи от пользователя
        telegram_user_id: ID пользователя в Telegram
        telegram_username: Username в Telegram (может быть None)
        telegram_name: Имя пользователя в Telegram
        files: Список файлов (пока только информация, без загрузки в Bitrix)
        
    Returns:
        ID созданной задачи в Bitrix
        
    Raises:
        BitrixClientError: При ошибке создания задачи
    """
    username_display = f"@{telegram_username}" if telegram_username else "нет username"
    
    # Информация о файлах
    files_info = ""
    if files:
        files_info = f"\n\n📎 Прикреплено файлов: {len(files)}"
        # TODO: В будущем можно реализовать загрузку файлов в Bitrix через disk.folder.uploadfile
    
    # Формируем описание задачи
    full_description = f"""🏢 Отдел: {department_name}
📍 Филиал: {branch}

📝 Описание задачи:
{description}
{files_info}
━━━━━━━━━━━━━━━━━━━━━━
👤 Отправитель: {telegram_name} ({username_display})
TG_USER_ID: {telegram_user_id}"""

    # Формируем название: [Филиал] Заголовок от пользователя
    task_title = f"[{branch}] {title}"

    params = {
        "fields": {
            "TITLE": task_title,
            "DESCRIPTION": full_description,
            "GROUP_ID": group_id,
            "RESPONSIBLE_ID": responsible_id,
            "PRIORITY": "1",
        }
    }
    
    logger.info(f"Creating task for user {telegram_user_id}, title: {title}, branch: {branch}")
    
    response = await call_method("tasks.task.add", params)
    
    task_id = response.get("result", {}).get("task", {}).get("id")
    if not task_id:
        logger.error(f"Unexpected response structure: {response}")
        raise BitrixClientError("Не удалось получить ID задачи из ответа")
    
    logger.info(f"Task created: #{task_id}")
    return int(task_id)


async def get_user_tasks(
    telegram_user_id: int, 
    limit: int = 30,
    only_active: bool = False,
) -> list[dict[str, Any]]:
    """
    Получить задачи пользователя по его Telegram ID из всех отделов.
    
    Args:
        telegram_user_id: ID пользователя в Telegram
        limit: Максимальное количество задач
        only_active: Если True — только незавершённые (статус != 5)
        
    Returns:
        Список задач пользователя с названием этапа Kanban и отдела
    """
    # Создаём маппинг group_id -> department_name
    group_to_dept = {
        dept["group_id"]: dept["name"]
        for dept in DEPARTMENTS.values()
        if dept["group_id"]
    }
    
    if not group_to_dept:
        logger.warning("No department group IDs configured")
        return []
    
    all_user_tasks = []
    
    for group_id, dept_name in group_to_dept.items():
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
            
            search_pattern = f"TG_USER_ID: {telegram_user_id}"
            for task in tasks:
                if search_pattern in task.get("description", ""):
                    # Фильтруем завершённые если нужно (статус 5 = завершена)
                    if only_active and str(task.get("status", "")) == "5":
                        continue
                    
                    stage_id = str(task.get("stageId", ""))
                    task["stage_name"] = stages.get(stage_id, "")
                    task["department_name"] = dept_name
                    all_user_tasks.append(task)
            
        except BitrixClientError as e:
            logger.warning(f"Failed to fetch tasks from group {group_id}: {e}")
            continue
    
    all_user_tasks.sort(key=lambda t: t.get("createdDate", ""), reverse=True)
    
    logger.info(f"Found {len(all_user_tasks)} tasks for user {telegram_user_id} (only_active={only_active})")
    
    return all_user_tasks[:limit]


def format_task_stage(stage_name: str) -> str:
    """Отформатировать название этапа для отображения."""
    if not stage_name:
        return "📋 Без этапа"
    return f"📋 {stage_name}"
