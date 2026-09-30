import os

import pytest
from httpx import ASGITransport, AsyncClient

from src.demo_audio import generate_demo_audio
from src.main import app

pytestmark = [
    pytest.mark.real_yamnet,
    pytest.mark.skipif(
        os.getenv("RUN_YAMNET_INTEGRATION") != "1",
        reason="Set RUN_YAMNET_INTEGRATION=1 to load/download the real YAMNet model",
    ),
]


@pytest.mark.asyncio
async def test_real_yamnet_audio_prediction():
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

    assert response.status_code == 200, response.text
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