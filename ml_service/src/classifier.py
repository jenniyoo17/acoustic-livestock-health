import numpy as np

CLASS_LABELS = (
    "Normal_Rumination",
    "Coughing_Spike",
    "Distress_Vocal",
    "Ambient_Noise",
)
CLASSIFIER_VERSION = "demo-untrained-mlp-v1"
EMBEDDING_DIMENSION = 1024


class DemoClassifier:
    """Deterministic untrained MLP for demonstrating the inference contract only."""

    def __init__(self, seed: int = 2026) -> None:
        rng = np.random.default_rng(seed)
        self._weights_1 = self._weight_matrix(rng, EMBEDDING_DIMENSION, 256)
        self._bias_1 = np.zeros(256, dtype=np.float32)
        self._weights_2 = self._weight_matrix(rng, 256, 64)
        self._bias_2 = np.zeros(64, dtype=np.float32)
        self._weights_3 = self._weight_matrix(rng, 64, len(CLASS_LABELS))
        self._bias_3 = np.zeros(len(CLASS_LABELS), dtype=np.float32)

    @staticmethod
    def _weight_matrix(rng: np.random.Generator, inputs: int, outputs: int) -> np.ndarray:
        scale = np.sqrt(2.0 / inputs)
        return rng.normal(0.0, scale, (inputs, outputs)).astype(np.float32)

    def predict(self, embedding: np.ndarray) -> tuple[str, float]:
        values = np.asarray(embedding, dtype=np.float32)
        if values.shape != (EMBEDDING_DIMENSION,):
            raise ValueError(f"Expected an embedding with shape ({EMBEDDING_DIMENSION},)")
        if not np.isfinite(values).all():
            raise ValueError("Embedding values must be finite")

        hidden_1 = np.maximum(values @ self._weights_1 + self._bias_1, 0)
        hidden_2 = np.maximum(hidden_1 @ self._weights_2 + self._bias_2, 0)
        logits = hidden_2 @ self._weights_3 + self._bias_3
        shifted_logits = logits - np.max(logits)
        probabilities = np.exp(shifted_logits)
        probabilities /= probabilities.sum()
        best_index = int(np.argmax(probabilities))
        return CLASS_LABELS[best_index], float(probabilities[best_index])

    @property
    def weights(self) -> list[np.ndarray]:
        return [
            self._weights_1,
            self._bias_1,
            self._weights_2,
            self._bias_2,
            self._weights_3,
            self._bias_3,
        ]