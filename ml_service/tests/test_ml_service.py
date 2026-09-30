import pytest
from httpx import ASGITransport, AsyncClient
import numpy as np

from src.demo_audio import generate_demo_audio
from src.main import app
from src.yamnet import YAMNetFeatureExtractor


@pytest.mark.asyncio
async def test_ml_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "acoustic-livestock-ml-service",
    }


@pytest.mark.asyncio
async def test_predict_accepts_synthetic_demo_audio(monkeypatch):
    class FakeFeatureExtractor:
        def extract(self, audio):
            assert audio.sample_rate == 16_000
            assert audio.waveform.dtype == np.float32
            return np.ones(1024, dtype=np.float32)

    monkeypatch.setattr(app.state, "feature_extractor", FakeFeatureExtractor())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/predict",
            files={
                "audio": (
                    "synthetic-cough.wav",
                    generate_demo_audio("Coughing_Spike"),
                    "audio/wav",
                )
            },
        )

    assert response.status_code == 200
    result = response.json()
    assert result["predicted_class"] in {
        "Normal_Rumination",
        "Coughing_Spike",
        "Distress_Vocal",
        "Ambient_Noise",
    }
    assert 0 <= result["confidence"] <= 1
    assert result["embedding_dimension"] == 1024
    assert result["processing_time_ms"] >= 0
    assert result["model_version"] == "demo-yamnet-v1"
    assert result["classifier_status"] == "UNTRAINED_DEMO"


@pytest.mark.asyncio
async def test_predict_rejects_invalid_audio():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/predict", files={"audio": ("invalid.wav", b"not audio", "audio/wav")}
        )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_predict_reports_unavailable_yamnet_without_fallback(monkeypatch):
    def unavailable_loader():
        raise ImportError("TensorFlow Hub is not installed")

    monkeypatch.setattr(
        app.state,
        "feature_extractor",
        YAMNetFeatureExtractor(model_loader=unavailable_loader),
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/predict",
            files={
                "audio": (
                    "synthetic-ambient.wav",
                    generate_demo_audio("Ambient_Noise"),
                    "audio/wav",
                )
            },
        )

    assert response.status_code == 503
    assert "Unable to load pretrained YAMNet" in response.json()["detail"]
