from dataclasses import dataclass
from io import BytesIO
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

TARGET_SAMPLE_RATE = 16_000


class AudioPreprocessingError(ValueError):
    """Raised when audio cannot be decoded or prepared for inference."""


class UnsupportedAudioFormatError(AudioPreprocessingError):
    """Raised when the input is not a supported audio stream."""


@dataclass(frozen=True)
class PreprocessedAudio:
    waveform: np.ndarray
    sample_rate: int = TARGET_SAMPLE_RATE


def preprocess_waveform(samples: np.ndarray, sample_rate: int) -> PreprocessedAudio:
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or sample_rate <= 0:
        raise AudioPreprocessingError("Sample rate must be a positive integer")

    waveform = np.asarray(samples, dtype=np.float32)
    if waveform.size == 0:
        raise AudioPreprocessingError("Audio is empty")
    if waveform.ndim not in (1, 2):
        raise AudioPreprocessingError("Audio must be mono or multichannel waveform data")
    if not np.isfinite(waveform).all():
        raise AudioPreprocessingError("Audio contains non-finite samples")

    if waveform.ndim == 2:
        waveform = waveform.mean(axis=1, dtype=np.float32)

    if sample_rate != TARGET_SAMPLE_RATE:
        divisor = gcd(sample_rate, TARGET_SAMPLE_RATE)
        waveform = resample_poly(
            waveform,
            TARGET_SAMPLE_RATE // divisor,
            sample_rate // divisor,
        ).astype(np.float32)

    if waveform.size == 0:
        raise AudioPreprocessingError("Audio is empty after resampling")

    peak = float(np.max(np.abs(waveform)))
    if peak > 0:
        waveform = waveform / peak

    return PreprocessedAudio(
        waveform=np.ascontiguousarray(waveform, dtype=np.float32),
        sample_rate=TARGET_SAMPLE_RATE,
    )


def preprocess_audio(audio_bytes: bytes) -> PreprocessedAudio:
    if not audio_bytes:
        raise AudioPreprocessingError("Audio upload is empty")

    try:
        samples, sample_rate = sf.read(
            BytesIO(audio_bytes), dtype="float32", always_2d=True
        )
    except (RuntimeError, ValueError, OSError) as error:
        raise UnsupportedAudioFormatError("Audio must be a supported WAV/audio file") from error

    return preprocess_waveform(samples, int(sample_rate))