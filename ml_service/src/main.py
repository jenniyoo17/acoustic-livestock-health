import os
from time import perf_counter

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict

from src.audio_preprocessing import AudioPreprocessingError, UnsupportedAudioFormatError, preprocess_audio
from src.classifier import DemoClassifier
from src.yamnet import YAMNetFeatureExtractor, YAMNetUnavailableError


class HealthResponse(BaseModel):
    status: str
    service: str


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    predicted_class: str
    confidence: float
    classifier_status: str = "UNTRAINED_DEMO"
    embedding_dimension: int
    processing_time_ms: float
    model_version: str


def create_app() -> FastAPI:
    service = FastAPI(title="Acoustic Livestock ML Service", version="0.1.0")
    service.state.feature_extractor = YAMNetFeatureExtractor(
        model_url=os.getenv("YAMNET_MODEL_URL", "https://tfhub.dev/google/yamnet/1")
    )
    service.state.classifier = DemoClassifier()

    @service.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        return HealthResponse(status="healthy", service="acoustic-livestock-ml-service")

    @service.post("/predict", response_model=PredictionResponse)
    async def predict_audio(
        request: Request,
        audio: UploadFile = File(..., description="Audio sample, preferably WAV"),
    ) -> PredictionResponse:
        started_at = perf_counter()
        audio_bytes = await audio.read()
        try:
            prepared_audio = preprocess_audio(audio_bytes)
        except UnsupportedAudioFormatError as error:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=str(error),
            ) from error
        except AudioPreprocessingError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error

        try:
            embedding = request.app.state.feature_extractor.extract(prepared_audio)
        except YAMNetUnavailableError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

        predicted_class, confidence = request.app.state.classifier.predict(embedding)
        return PredictionResponse(
            predicted_class=predicted_class,
            confidence=confidence,
            embedding_dimension=int(embedding.shape[0]),
            processing_time_ms=(perf_counter() - started_at) * 1000,
            model_version="demo-yamnet-v1",
        )

    return service


app = create_app()
