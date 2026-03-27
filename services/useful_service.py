from __future__ import annotations

import logging
from dataclasses import dataclass

from database import AsyncSessionLocal, DepartmentType, get_department_buttons

logger = logging.getLogger(__name__)

DEPARTMENT_LABELS = {
    DepartmentType.DEVELOPMENT: "Отдел Развития",
    DepartmentType.MARKETING: "Отдел Маркетинга",
    DepartmentType.DESIGN: "Дизайн",
}


@dataclass
class DepartmentItem:
    key: str
    name: str


@dataclass
class ButtonItem:
    id: int
    button_text: str
    message_text: str


def get_departments() -> list[DepartmentItem]:
    return [
        DepartmentItem(key=dt.value, name=DEPARTMENT_LABELS.get(dt, dt.value))
        for dt in DepartmentType
    ]


async def get_department_content(dept_key: str) -> list[ButtonItem]:
    dept = DepartmentType(dept_key)
    async with AsyncSessionLocal() as db:
        buttons = await get_department_buttons(db, dept)

    return [
        ButtonItem(id=b.id, button_text=b.button_text, message_text=b.message_text or "")
        for b in buttons
    ]
