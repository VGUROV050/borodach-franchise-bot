from fastapi import APIRouter, Depends, HTTPException

from database import AsyncSessionLocal, get_partner_by_id
from bitrix import BitrixClientError
from mobile_api.deps import get_current_partner_id
from mobile_api.schemas import (
    TaskDepartmentOut,
    TaskOut,
    TaskCreateIn,
    TaskCreateOut,
    TaskCancelOut,
)
from services.task_service import (
    get_departments_list,
    get_tasks,
    create_new_task,
    cancel_user_task,
)

router = APIRouter()


async def _get_partner_telegram_id(partner_id: int) -> int:
    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_id(db, partner_id)
    if not partner or not partner.telegram_id:
        raise HTTPException(status_code=404, detail="Partner or telegram_id not found")
    return partner.telegram_id


@router.get("/tasks/departments", response_model=list[TaskDepartmentOut])
async def list_task_departments():
    depts = get_departments_list()
    return [
        TaskDepartmentOut(
            key=d.key,
            name=d.name,
            group_id=d.group_id,
            responsible_id=d.responsible_id,
        )
        for d in depts
    ]


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    active_only: bool = True,
    partner_id: int = Depends(get_current_partner_id),
):
    telegram_id = await _get_partner_telegram_id(partner_id)
    items = await get_tasks(telegram_id, only_active=active_only)
    return [
        TaskOut(
            id=t.id,
            title=t.title,
            barbershop=t.barbershop,
            created_at=t.created_date,
            stage=t.stage,
            stage_emoji=t.stage_emoji,
            group_id=t.group_id,
            department_name=t.department_name,
        )
        for t in items
    ]


@router.post("/tasks", response_model=TaskCreateOut)
async def create_task_endpoint(
    body: TaskCreateIn,
    partner_id: int = Depends(get_current_partner_id),
):
    depts = {d.key: d for d in get_departments_list()}
    dept = depts.get(body.department_key)
    if not dept:
        raise HTTPException(status_code=400, detail="Unknown department")

    async with AsyncSessionLocal() as db:
        partner = await get_partner_by_id(db, partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    try:
        task_id = await create_new_task(
            group_id=dept.group_id,
            responsible_id=dept.responsible_id,
            department_name=dept.name,
            barbershop=body.barbershop,
            title=body.title,
            description=body.description,
            telegram_user_id=partner.telegram_id,
            telegram_username=getattr(partner, "telegram_username", None),
            telegram_name=partner.full_name,
        )
    except BitrixClientError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return TaskCreateOut(task_id=task_id)


@router.post("/tasks/{task_id}/cancel", response_model=TaskCancelOut)
async def cancel_task_endpoint(
    task_id: int,
    partner_id: int = Depends(get_current_partner_id),
):
    telegram_id = await _get_partner_telegram_id(partner_id)
    success = await cancel_user_task(task_id, telegram_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel this task",
        )
    return TaskCancelOut(success=True)
