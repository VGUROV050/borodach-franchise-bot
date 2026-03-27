from fastapi import APIRouter, HTTPException

from mobile_api.schemas import DepartmentOut, DepartmentButtonOut
from services.useful_service import get_departments, get_department_content

router = APIRouter()


@router.get("/useful/departments", response_model=list[DepartmentOut])
async def list_departments():
    depts = get_departments()
    return [DepartmentOut(key=d.key, name=d.name) for d in depts]


@router.get(
    "/useful/departments/{dept_key}/buttons",
    response_model=list[DepartmentButtonOut],
)
async def list_department_buttons(dept_key: str):
    try:
        buttons = await get_department_content(dept_key)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown department")

    return [
        DepartmentButtonOut(id=b.id, button_text=b.button_text, message_text=b.message_text)
        for b in buttons
    ]
