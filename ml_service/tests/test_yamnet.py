import numpy as np
import pytest

from src.audio_preprocessing import PreprocessedAudio, TARGET_SAMPLE_RATE
from src.yamnet import EMBEDDING_DIMENSION, YAMNetFeatureExtractor


def test_yamnet_extractor_returns_1024_dimension_embedding_and_reuses_model():
    load_calls = 0

    def loader():
        nonlocal load_calls
        load_calls += 1

        def model(waveform):
            assert waveform.dtype == np.float32
            return (
                np.zeros((2, 521), dtype=np.float32),
                np.ones((2, EMBEDDING_DIMENSION), dtype=np.float32),
                np.zeros((1, 64), dtype=np.float32),
            )

        return model

    extractor = YAMNetFeatureExtractor(model_loader=loader)
    audio = PreprocessedAudio(np.zeros(TARGET_SAMPLE_RATE, dtype=np.float32))

    first = extractor.extract(audio)
    second = extractor.extract(audio)

    assert first.shape == (EMBEDDING_DIMENSION,)
    assert np.array_equal(first, second)
    assert load_calls == 1
    assert extractor.is_loaded


def test_yamnet_extractor_rejects_unexpected_embedding_dimension():
    extractor = YAMNetFeatureExtractor(
        model_loader=lambda: lambda waveform: (None, np.zeros((1, 512)), None)
    )
    audio = PreprocessedAudio(np.zeros(100, dtype=np.float32))

    with pytest.raises(RuntimeError, match="Expected 1024-dimensional"):
        extractor.extract(audio)