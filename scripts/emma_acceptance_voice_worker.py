from __future__ import annotations

import argparse
import json
import os
import sys
import types
from pathlib import Path
from typing import Any


def install_numba_compatibility_shim() -> None:
    if "numba" in sys.modules:
        return
    module = types.ModuleType("numba")

    def decorator(*args: Any, **_kwargs: Any) -> Any:
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


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate final Emma acceptance narration batch.")
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8-sig"))
    model_path = Path(job["modelPath"]).resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(str(model_path))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    install_numba_compatibility_shim()

    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    model = Qwen3TTSModel.from_pretrained(
        str(model_path),
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    clone_prompt = model.create_voice_clone_prompt(
        ref_audio=job["referenceAudio"],
        ref_text=job["referenceText"],
        x_vector_only_mode=False,
    )
    records = []
    for index, item in enumerate(job["cases"], start=1):
        seed = int(item.get("seed", 260724 + index))
        wavs = []
        sample_rate = 24000
        for retry in range(3):
            selected_seed = seed + retry * 1009
            torch.manual_seed(selected_seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(selected_seed)
            wavs, sample_rate = model.generate_voice_clone(
                text=item["text"],
                language="Chinese",
                voice_clone_prompt=clone_prompt,
            )
            if wavs and len(wavs[0]) / sample_rate >= 1.0:
                seed = selected_seed
                break
        if not wavs or len(wavs[0]) / sample_rate < 1.0:
            raise RuntimeError(
                f"Qwen3-TTS returned empty speech after retries: {item['caseId']}"
            )
        output = Path(item["output"]).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output), wavs[0], sample_rate)
        records.append(
            {
                "caseId": item["caseId"],
                "text": item["text"],
                "path": str(output),
                "sampleRate": sample_rate,
                "bytes": output.stat().st_size,
                "seed": seed,
                "provenance": "real-production",
            }
        )
    report = {
        "schema": "temple-ai-studio.emma-commercial-acceptance-voice-batch.v1",
        "provider": "qwen3-tts-local",
        "model": str(model_path),
        "profileId": job["profileId"],
        "referenceAudio": job["referenceAudio"],
        "caseCount": len(records),
        "records": records,
        "overall": "PASS" if len(records) == len(job["cases"]) else "FAIL",
    }
    atomic_json(Path(args.output), report)
    print(json.dumps({"overall": report["overall"], "count": len(records)}))
    return 0 if report["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
