from io import BytesIO

import numpy as np
import pytest
import soundfile as sf

from src.audio_preprocessing import (
    AudioPreprocessingError,
    TARGET_SAMPLE_RATE,
    UnsupportedAudioFormatError,
    preprocess_audio,
    preprocess_waveform,
)


def wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    buffer = BytesIO()
    sf.write(buffer, samples, sample_rate, format="WAV", subtype="FLOAT")
    return buffer.getvalue()


def test_preprocess_converts_stereo_to_normalized_mono():
    samples = np.column_stack(
        [np.sin(np.linspace(0, 20, 16000)), np.sin(np.linspace(0, 20, 16000)) * 0.5]
    ).astype(np.float32)

    result = preprocess_audio(wav_bytes(samples, TARGET_SAMPLE_RATE))

    assert result.sample_rate == TARGET_SAMPLE_RATE
    assert result.waveform.ndim == 1
    assert result.waveform.dtype == np.float32
    assert np.max(np.abs(result.waveform)) == pytest.approx(1.0)


def test_preprocess_resamples_to_16khz():
    samples = np.sin(np.linspace(0, 30, 48_000, dtype=np.float32))

    result = preprocess_audio(wav_bytes(samples, 48_000))

    assert result.sample_rate == TARGET_SAMPLE_RATE
    assert result.waveform.shape == (TARGET_SAMPLE_RATE,)
    assert np.isfinite(result.waveform).all()


def test_preprocess_rejects_empty_and_invalid_audio():
    with pytest.raises(AudioPreprocessingError, match="empty"):
        preprocess_audio(b"")
    with pytest.raises(UnsupportedAudioFormatError):
        preprocess_audio(b"not an audio file")


@pytest.mark.parametrize("sample_rate", [0, -1, 16_000.5, True])
def test_preprocess_rejects_invalid_sample_rate(sample_rate):
    with pytest.raises(AudioPreprocessingError, match="Sample rate"):
        preprocess_waveform(np.ones(10, dtype=np.float32), sample_rate)


def test_preprocess_rejects_empty_waveform():
    with pytest.raises(AudioPreprocessingError, match="empty"):
        preprocess_waveform(np.array([], dtype=np.float32), TARGET_SAMPLE_RATE)