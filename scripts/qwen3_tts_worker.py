from __future__ import annotations

import argparse
import json
import os
import sys
import types
from pathlib import Path


def _install_numba_compatibility_shim() -> None:
    """Librosa only needs the decorator surface for Qwen inference on this host."""
    if "numba" in sys.modules:
        return
    module = types.ModuleType("numba")

    def decorator(*args, **_kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda function: function

    module.jit = decorator
    module.njit = decorator
    module.guvectorize = decorator
    module.vectorize = decorator
    module.stencil = decorator
    module.prange = range
    sys.modules["numba"] = module


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio Qwen3-TTS production worker.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", default="Chinese")
    parser.add_argument(
        "--mode",
        choices=["voice-design", "custom-voice", "voice-clone"],
        default="voice-clone",
    )
    parser.add_argument("--instruct", default="")
    parser.add_argument("--speaker", default="")
    parser.add_argument("--reference-audio")
    parser.add_argument("--reference-text")
    parser.add_argument("--seed", type=int, default=260724)
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    output = Path(args.output).resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"Local Qwen3-TTS model not found: {model_path}")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    _install_numba_compatibility_shim()
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    model = Qwen3TTSModel.from_pretrained(
        str(model_path),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    if args.mode == "voice-design":
        if not args.instruct.strip():
            raise ValueError("--instruct is required for voice-design mode.")
        wavs, sample_rate = model.generate_voice_design(
            text=args.text,
            language=args.language,
            instruct=args.instruct,
        )
    elif args.mode == "custom-voice":
        if not args.speaker.strip():
            raise ValueError("--speaker is required for custom-voice mode.")
        wavs, sample_rate = model.generate_custom_voice(
            text=args.text,
            language=args.language,
            speaker=args.speaker,
            instruct=args.instruct,
        )
    else:
        if not args.reference_audio or not args.reference_text:
            raise ValueError(
                "--reference-audio and --reference-text are required for voice-clone mode."
            )
        reference_audio = Path(args.reference_audio).resolve()
        if not reference_audio.is_file():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio}")
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
                "mode": args.mode,
                "seed": args.seed,
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
