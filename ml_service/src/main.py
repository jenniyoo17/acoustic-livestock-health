from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Acoustic Livestock ML Service", version="0.1.0")


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", service="acoustic-livestock-ml-service")
