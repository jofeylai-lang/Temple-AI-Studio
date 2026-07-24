from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Qwen3-TTS production worker.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--reference-audio", required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    reference_audio = Path(args.reference_audio).resolve()
    output = Path(args.output).resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"Local Qwen3-TTS model not found: {model_path}")
    if not reference_audio.is_file():
        raise FileNotFoundError(f"Reference audio not found: {reference_audio}")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    model = Qwen3TTSModel.from_pretrained(
        str(model_path),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    wavs, sample_rate = model.generate_voice_clone(
        text=args.text,
        language=args.language,
        ref_audio=str(reference_audio),
        ref_text=args.reference_text,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output), wavs[0], sample_rate)
    print(
        json.dumps(
            {
                "provider": "qwen3-tts-local",
                "model": str(model_path),
                "output": str(output),
                "sampleRate": sample_rate,
                "provenance": "real-production",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
