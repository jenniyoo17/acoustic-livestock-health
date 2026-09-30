from fastapi import FastAPI

from app.api.v1.health import router as health_router

app = FastAPI(
    title="Acoustic Livestock Health Backend",
    version="0.1.0",
    description="Acoustic early-warning anomaly detection only. Veterinary verification required.",
)

app.include_router(health_router)
