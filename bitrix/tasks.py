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
                    stage_id = str(task.get("stageId", ""))
                    stage_name = stages.get(stage_id, "")
                    
                    # Фильтруем завершённые и отменённые если нужны только активные
                    if only_active:
                        # Статус 5 = завершена
                        if str(task.get("status", "")) == "5":
                            continue
                        # Этап "Отменена"
                        if "отменен" in stage_name.lower():
                            continue
                    
                    task["stage_name"] = stage_name
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


async def get_task_by_id(task_id: int) -> dict[str, Any] | None:
    """
    Получить задачу по ID.
    
    Args:
        task_id: ID задачи в Bitrix
        
    Returns:
        Данные задачи или None, если не найдена
    """
    params = {
        "taskId": task_id,
        "select": ["ID", "TITLE", "STATUS", "STAGE_ID", "DESCRIPTION", "GROUP_ID"],
    }
    
    try:
        response = await call_method("tasks.task.get", params)
        task = response.get("result", {}).get("task", {})
        return task if task else None
    except BitrixClientError as e:
        logger.warning(f"Failed to get task {task_id}: {e}")
        return None


async def get_cancelled_stage_id(group_id: str) -> str | None:
    """
    Найти ID этапа "Отменена" в проекте.
    
    Args:
        group_id: ID проекта/группы в Bitrix
        
    Returns:
        ID этапа "Отменена" или None, если не найден
    """
    stages = await get_project_stages(group_id)
    
    # Ищем этап с названием "Отменена" (или похожим)
    for stage_id, stage_name in stages.items():
        if "отменен" in stage_name.lower():
            return stage_id
    
    logger.warning(f"Cancelled stage not found in group {group_id}")
    return None


async def cancel_task(task_id: int, group_id: str) -> bool:
    """
    Отменить задачу — перевести на этап "Отменена".
    
    Args:
        task_id: ID задачи
        group_id: ID проекта/группы задачи
        
    Returns:
        True, если успешно, False иначе
    """
    cancelled_stage_id = await get_cancelled_stage_id(group_id)
    
    if not cancelled_stage_id:
        logger.error(f"Cannot cancel task {task_id}: no 'Отменена' stage in group {group_id}")
        return False
    
    params = {
        "taskId": task_id,
        "fields": {
            "STAGE_ID": cancelled_stage_id,
        }
    }
    
    try:
        await call_method("tasks.task.update", params)
        logger.info(f"Task {task_id} moved to cancelled stage {cancelled_stage_id}")
        return True
    except BitrixClientError as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return False


def verify_task_ownership(task: dict[str, Any], telegram_user_id: int) -> bool:
    """
    Проверить, что задача принадлежит пользователю.
    
    Args:
        task: Данные задачи из Bitrix
        telegram_user_id: ID пользователя в Telegram
        
    Returns:
        True, если задача принадлежит пользователю
    """
    description = task.get("description", "")
    search_pattern = f"TG_USER_ID: {telegram_user_id}"
    return search_pattern in description


async def check_task_can_be_cancelled(task: dict[str, Any]) -> tuple[bool, str]:
    """
    Проверить, можно ли отменить задачу.
    
    Args:
        task: Данные задачи из Bitrix
        
    Returns:
        (can_cancel, reason) - можно ли отменить и причина если нет
    """
    # Проверяем статус (5 = завершена)
    if str(task.get("status", "")) == "5":
        return False, "completed"
    
    # Проверяем этап Kanban
    group_id = str(task.get("groupId", ""))
    if group_id:
        stages = await get_project_stages(group_id)
        stage_id = str(task.get("stageId", ""))
        stage_name = stages.get(stage_id, "")
        
        if "отменен" in stage_name.lower():
            return False, "cancelled"
    
    return True, ""
