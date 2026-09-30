import argparse
from io import BytesIO
from pathlib import Path

import numpy as np
import soundfile as sf

from src.audio_preprocessing import TARGET_SAMPLE_RATE
from src.classifier import CLASS_LABELS


def generate_demo_audio(
    class_name: str,
    duration_sec: float = 0.96,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> bytes:
    """Generate a deterministic synthetic signal, not a livestock recording."""
    if class_name not in CLASS_LABELS:
        raise ValueError(f"class_name must be one of {CLASS_LABELS}")
    if duration_sec <= 0 or sample_rate <= 0:
        raise ValueError("duration_sec and sample_rate must be positive")

    sample_count = int(duration_sec * sample_rate)
    time = np.arange(sample_count, dtype=np.float32) / sample_rate
    rng = np.random.default_rng(CLASS_LABELS.index(class_name) + 2026)

    if class_name == "Normal_Rumination":
        modulation = 0.55 + 0.45 * np.sin(2 * np.pi * 2.5 * time)
        waveform = modulation * np.sin(2 * np.pi * 72 * time)
        waveform += 0.25 * np.sin(2 * np.pi * 144 * time)
        waveform += 0.02 * rng.standard_normal(sample_count)
    elif class_name == "Coughing_Spike":
        waveform = 0.015 * rng.standard_normal(sample_count)
        for center in (0.24, 0.62):
            envelope = np.exp(-0.5 * ((time - center) / 0.025) ** 2)
            waveform += envelope * 0.6 * rng.standard_normal(sample_count)
    elif class_name == "Distress_Vocal":
        sweep = 260 * time + 85 * time**2
        waveform = 0.55 * np.sin(2 * np.pi * sweep)
        waveform += 0.18 * np.sin(2 * np.pi * 2 * sweep)
        waveform += 0.02 * rng.standard_normal(sample_count)
    else:
        waveform = 0.12 * rng.standard_normal(sample_count)

    peak = float(np.max(np.abs(waveform)))
    if peak > 0:
        waveform = waveform / peak * 0.9

    output = BytesIO()
    sf.write(output, waveform.astype(np.float32), sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a synthetic demo-only WAV sample")
    parser.add_argument("class_name", choices=CLASS_LABELS)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_bytes(generate_demo_audio(args.class_name))
    print(f"Wrote synthetic demo signal to {args.output}; it is not a livestock recording.")


if __name__ == "__main__":
    main()