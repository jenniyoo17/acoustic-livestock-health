import numpy as np
import pytest

from src.classifier import CLASS_LABELS, DemoClassifier, EMBEDDING_DIMENSION


def test_demo_classifier_returns_one_of_four_classes_and_valid_confidence():
    classifier = DemoClassifier()

    predicted_class, confidence = classifier.predict(np.ones(EMBEDDING_DIMENSION, dtype=np.float32))

    assert predicted_class in CLASS_LABELS
    assert 0 <= confidence <= 1


def test_demo_classifier_is_deterministic():
    embedding = np.linspace(-1, 1, EMBEDDING_DIMENSION, dtype=np.float32)
    first = DemoClassifier().predict(embedding)
    second = DemoClassifier().predict(embedding)

    assert first == second


@pytest.mark.parametrize("embedding", [np.zeros(512), np.full(1024, np.nan)])
def test_demo_classifier_rejects_invalid_embeddings(embedding):
    with pytest.raises(ValueError):
        DemoClassifier().predict(embedding)