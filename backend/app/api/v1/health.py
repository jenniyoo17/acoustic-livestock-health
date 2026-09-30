from fastapi import APIRouter
from pydantic import BaseModel
from app.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


@router.get("", response_model=HealthResponse)
async def get_health_status():
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )
