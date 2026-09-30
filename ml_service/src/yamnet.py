from collections.abc import Callable
from typing import Any

import numpy as np

from src.audio_preprocessing import PreprocessedAudio, TARGET_SAMPLE_RATE

YAMNET_MODEL_URL = "https://tfhub.dev/google/yamnet/1"
EMBEDDING_DIMENSION = 1024


class YAMNetUnavailableError(RuntimeError):
    """Raised when the real pretrained YAMNet model cannot be loaded or run."""


class YAMNetFeatureExtractor:
    """Loads YAMNet once and returns the mean 1024-value frame embedding."""

    def __init__(
        self,
        model_url: str = YAMNET_MODEL_URL,
        model_loader: Callable[[], Callable[..., Any]] | None = None,
    ) -> None:
        self.model_url = model_url
        self._model_loader = model_loader
        self._model: Callable[..., Any] | None = None
        self._tensorflow: Any | None = None
        self._load_error: Exception | None = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _load(self) -> None:
        if self._model is not None:
            return
        if self._load_error is not None:
            raise YAMNetUnavailableError(
                f"YAMNet is unavailable: {self._load_error}"
            ) from self._load_error

        try:
            if self._model_loader is not None:
                self._model = self._model_loader()
                return

            import tensorflow as tf
            import tensorflow_hub as hub

            self._model = hub.load(self.model_url)
            self._tensorflow = tf
        except Exception as error:
            self._load_error = error
            raise YAMNetUnavailableError(
                f"Unable to load pretrained YAMNet from {self.model_url}: {error}"
            ) from error

    def extract(self, audio: PreprocessedAudio) -> np.ndarray:
        if audio.sample_rate != TARGET_SAMPLE_RATE:
            raise ValueError("YAMNet input must be sampled at 16 kHz")
        waveform = np.asarray(audio.waveform, dtype=np.float32)
        if waveform.ndim != 1 or waveform.size == 0 or not np.isfinite(waveform).all():
            raise ValueError("YAMNet input must be a non-empty finite mono waveform")

        self._load()
        model_input = waveform
        if self._tensorflow is not None:
            model_input = self._tensorflow.convert_to_tensor(waveform, dtype=self._tensorflow.float32)

        try:
            output = self._model(model_input)
            embedding_frames = output[1] if isinstance(output, (tuple, list)) else output
            if hasattr(embedding_frames, "numpy"):
                embedding_frames = embedding_frames.numpy()
            embedding_frames = np.asarray(embedding_frames, dtype=np.float32)
        except Exception as error:
            raise YAMNetUnavailableError(f"YAMNet inference failed: {error}") from error

        if embedding_frames.ndim != 2 or embedding_frames.shape[0] == 0:
            raise YAMNetUnavailableError("YAMNet returned no embedding frames")
        if embedding_frames.shape[1] != EMBEDDING_DIMENSION:
            raise YAMNetUnavailableError(
                f"Expected {EMBEDDING_DIMENSION}-dimensional YAMNet embeddings, "
                f"received shape {embedding_frames.shape}"
            )
        if not np.isfinite(embedding_frames).all():
            raise YAMNetUnavailableError("YAMNet returned non-finite embedding values")

        return embedding_frames.mean(axis=0, dtype=np.float32)