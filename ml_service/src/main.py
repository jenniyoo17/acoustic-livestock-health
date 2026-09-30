from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

app = FastAPI(
    title="SIH 2026 Acoustic Livestock ML Service",
    version="0.1.0",
    description="YAMNet Feature Extraction & TFLite Model Re-validation Service Placeholder",
)


class MLHealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    service: str
    model_version: str


@app.get("/health", response_model=MLHealthResponse)
async def ml_health_check():
    return MLHealthResponse(
        status="healthy",
        service="acoustic-livestock-ml-service",
        model_version="YAMNet-TFLite-v1.0-placeholder",
    )
