from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="SIH 2026 Edge AI Device Simulator",
    version="0.1.0",
    description="Offline-First Edge Audio Sensing Device Simulator Placeholder",
)


class EdgeHealthResponse(BaseModel):
    status: str
    service: str
    device_mode: str


@app.get("/health", response_model=EdgeHealthResponse)
async def edge_health_check():
    return EdgeHealthResponse(
        status="healthy",
        service="acoustic-livestock-edge-simulator",
        device_mode="online_simulated",
    )
