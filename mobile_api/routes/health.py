# Mobile API — health check route

from fastapi import APIRouter

from mobile_api.schemas import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health_check():
    return HealthOut(status="ok", version="0.1.0")
