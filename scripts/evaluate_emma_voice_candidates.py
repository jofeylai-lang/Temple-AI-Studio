from __future__ import annotations

import argparse
import json
import sys
import types
from itertools import combinations
from pathlib import Path
from typing import Any


def install_numba_compatibility_shim() -> None:
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


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Emma voice candidate distinctness with WavLM.")
    parser.add_argument("--candidate-report", required=True)
    parser.add_argument("--wavlm-model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    install_numba_compatibility_shim()

    import numpy as np
    import soundfile as sf
    import torch
    import torch.nn.functional as functional
    from transformers import AutoFeatureExtractor, AutoModelForAudioXVector

    report_path = Path(args.candidate_report).resolve()
    source = json.loads(report_path.read_text(encoding="utf-8"))
    model_path = Path(args.wavlm_model).resolve()
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    extractor = AutoFeatureExtractor.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModelForAudioXVector.from_pretrained(
        str(model_path),
        local_files_only=True,
    ).to(device)
    model.eval()
    embeddings = {}
    for candidate in source["candidates"]:
        audio, sample_rate = sf.read(candidate["path"], always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        tensor = torch.asarray(audio, dtype=torch.float32)
        if sample_rate != 16000:
            output_length = round(len(tensor) * 16000 / sample_rate)
            tensor = functional.interpolate(
                tensor.view(1, 1, -1),
                size=output_length,
                mode="linear",
                align_corners=False,
            ).view(-1)
        inputs = extractor(
            tensor.numpy(),
            sampling_rate=16000,
            return_tensors="pt",
            padding=True,
        )
        with torch.inference_mode():
            embedding = model(
                input_values=inputs.input_values.to(device),
                attention_mask=inputs.get("attention_mask", None).to(device)
                if inputs.get("attention_mask", None) is not None
                else None,
            ).embeddings[0]
            embedding = functional.normalize(embedding, dim=0).detach().cpu().numpy()
        embeddings[candidate["number"]] = embedding

    pairs = []
    for first, second in combinations(sorted(embeddings), 2):
        similarity = float(np.dot(embeddings[first], embeddings[second]))
        pairs.append(
            {
                "first": first,
                "second": second,
                "cosineSimilarity": round(similarity, 5),
                "distinct": similarity < 0.985,
            }
        )
    matrix = []
    numbers = sorted(embeddings)
    for first in numbers:
        matrix.append(
            [
                round(float(np.dot(embeddings[first], embeddings[second])), 5)
                for second in numbers
            ]
        )
    evaluation = {
        "schema": "temple-ai-studio.emma-voice-wavlm-evaluation.v1",
        "overall": "PASS" if all(pair["distinct"] for pair in pairs) else "FAIL",
        "engine": "microsoft/wavlm-base-plus-sv",
        "model": str(model_path),
        "device": device,
        "realPersonCloning": False,
        "candidateCount": len(numbers),
        "numbers": numbers,
        "pairwiseCosineMatrix": matrix,
        "pairs": pairs,
        "minimumPairDistance": round(
            min(1.0 - pair["cosineSimilarity"] for pair in pairs),
            5,
        ),
        "maximumPairSimilarity": round(
            max(pair["cosineSimilarity"] for pair in pairs),
            5,
        ),
    }
    output = Path(args.output).resolve()
    atomic_json(output, evaluation)
    source["wavlmEvaluation"] = str(output)
    source["wavlmOverall"] = evaluation["overall"]
    atomic_json(report_path, source)
    print(json.dumps(evaluation, ensure_ascii=False))
    return 0 if evaluation["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
