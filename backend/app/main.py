from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.api.v1 import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup logic
    yield
    # Application shutdown logic


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SIH 2026 AI-based Acoustic Livestock Health Early-Warning System Backend",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RootHealthResponse(BaseModel):
    status: str
    service: str
    version: str
    disclaimer: str


@app.get("/health", response_model=RootHealthResponse, tags=["Health"])
async def root_health_check():
    """Root Health Status Endpoint as specified in Milestone 1 requirement"""
    return RootHealthResponse(
        status="healthy",
        service="acoustic-livestock-health-backend",
        version=settings.VERSION,
        disclaimer="Early-warning anomaly alert system. Clinical veterinary verification required.",
    )


# Include API v1 routes
app.include_router(api_v1_router, prefix="/api/v1")
