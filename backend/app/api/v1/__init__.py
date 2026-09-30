from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.edge import router as edge_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, prefix="/health", tags=["Health"])
api_v1_router.include_router(edge_router, prefix="/edge", tags=["Edge Ingestion"])
