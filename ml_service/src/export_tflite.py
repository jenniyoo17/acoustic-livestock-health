import argparse
from pathlib import Path

from src.classifier import CLASS_LABELS, DemoClassifier, EMBEDDING_DIMENSION


def export_float16(destination: Path) -> Path:
    """Export the untrained demo classifier as a compact FP16 TFLite model."""
    try:
        import tensorflow as tf
    except ImportError as error:
        raise RuntimeError("TensorFlow is required for TFLite export") from error

    keras_model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(EMBEDDING_DIMENSION,), name="yamnet_embedding"),
            tf.keras.layers.Dense(256, activation="relu"),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(len(CLASS_LABELS), activation="softmax"),
        ],
        name="untrained_demo_livestock_classifier",
    )
    keras_model.set_weights(DemoClassifier().weights)

    converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    model_bytes = converter.convert()

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(model_bytes)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the untrained demo classifier to FP16 TFLite")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output_path = export_float16(args.output)
    print(f"Exported untrained demo classifier to {output_path} ({output_path.stat().st_size} bytes).")


if __name__ == "__main__":
    main()