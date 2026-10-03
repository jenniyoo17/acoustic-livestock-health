from fastapi import FastAPI

from app.api.v1.alerts import router as alerts_router
from app.api.v1.edge import router as edge_router
from app.api.v1.health import router as health_router
from app.api.v1.lab import router as lab_router
from app.api.v1.vet import router as vet_router

app = FastAPI(
    title="Acoustic Livestock Health Backend",
    version="0.1.0",
    description="Acoustic early-warning anomaly detection only. Veterinary verification required.",
)

app.include_router(health_router)
app.include_router(edge_router, prefix="/api/v1/edge", tags=["Edge Ingestion"])
app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(vet_router, prefix="/api/v1/vet", tags=["Veterinary Verification"])
app.include_router(lab_router, prefix="/api/v1/lab", tags=["Lab Referrals"])
