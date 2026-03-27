from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from config.settings import DEPARTMENTS
from bitrix import (
    create_task,
    get_user_tasks,
    get_task_by_id,
    cancel_task,
    verify_task_ownership,
    check_task_can_be_cancelled,
    BitrixClientError,
)

logger = logging.getLogger(__name__)

_TITLE_RE = re.compile(r"^\[(.+?)]\s*(.+)$")


@dataclass
class DepartmentInfo:
    key: str
    name: str
    group_id: str
    responsible_id: str


STAGE_EMOJI = {
    "новая": "🆕",
    "выполня": "⏳",
    "проверк": "👀",
    "заверш": "✅",
    "выполнен": "✅",
    "отменен": "🚫",
}


def _get_stage_emoji(stage_name: str) -> str:
    stage_lower = stage_name.lower()
    for pattern, emoji in STAGE_EMOJI.items():
        if pattern in stage_lower:
            return emoji
    return "📋"


@dataclass
class TaskItem:
    id: int
    title: str
    barbershop: Optional[str]
    created_date: str
    stage: str
    stage_emoji: str
    group_id: str
    department_name: str


def get_departments_list() -> list[DepartmentInfo]:
    return [
        DepartmentInfo(
            key=key,
            name=cfg["name"],
            group_id=cfg["group_id"],
            responsible_id=cfg["responsible_id"],
        )
        for key, cfg in DEPARTMENTS.items()
        if cfg.get("group_id")
    ]


def _parse_title(raw_title: str) -> tuple[Optional[str], str]:
    m = _TITLE_RE.match(raw_title)
    if m:
        return m.group(1), m.group(2)
    return None, raw_title


async def get_tasks(telegram_id: int, only_active: bool = True) -> list[TaskItem]:
    raw_tasks = await get_user_tasks(telegram_id, limit=50, only_active=only_active)

    items: list[TaskItem] = []
    for t in raw_tasks:
        barbershop, title = _parse_title(t.get("title", ""))
        stage_name = t.get("stage_name", "")
        items.append(
            TaskItem(
                id=int(t.get("id", 0)),
                title=title,
                barbershop=barbershop,
                created_date=t.get("createdDate", ""),
                stage=stage_name,
                stage_emoji=_get_stage_emoji(stage_name),
                group_id=str(t.get("groupId", "")),
                department_name=t.get("department_name", ""),
            )
        )
    return items


async def create_new_task(
    group_id: str,
    responsible_id: str,
    department_name: str,
    barbershop: str,
    title: str,
    description: str,
    telegram_user_id: int,
    telegram_username: Optional[str],
    telegram_name: str,
) -> int:
    return await create_task(
        group_id=group_id,
        responsible_id=responsible_id,
        department_name=department_name,
        branch=barbershop,
        title=title,
        description=description,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        telegram_name=telegram_name,
    )


async def cancel_user_task(task_id: int, telegram_id: int) -> bool:
    task = await get_task_by_id(task_id)
    if not task:
        return False

    if not verify_task_ownership(task, telegram_id):
        return False

    can_cancel, _ = await check_task_can_be_cancelled(task)
    if not can_cancel:
        return False

    group_id = str(task.get("groupId", ""))
    return await cancel_task(task_id, group_id)
