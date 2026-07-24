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
    parser = argparse.ArgumentParser(description="Evaluate canonical Emma voice consistency.")
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8-sig"))
    install_numba_compatibility_shim()

    import numpy as np
    import soundfile as sf
    import torch
    import torch.nn.functional as functional
    from transformers import AutoFeatureExtractor, AutoModelForAudioXVector

    model_path = Path(job["modelPath"]).resolve()
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    extractor = AutoFeatureExtractor.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModelForAudioXVector.from_pretrained(
        str(model_path),
        local_files_only=True,
    ).to(device)
    model.eval()

    def embedding(path: str) -> Any:
        audio, sample_rate = sf.read(path, always_2d=False)
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
            vector = model(
                input_values=inputs.input_values.to(device),
                attention_mask=inputs.get("attention_mask", None).to(device)
                if inputs.get("attention_mask", None) is not None
                else None,
            ).embeddings[0]
        return functional.normalize(vector, dim=0).detach().cpu().numpy()

    records = job["segments"]
    embeddings = {item["segmentId"]: embedding(item["path"]) for item in records}
    pairs = []
    for left, right in combinations(records, 2):
        similarity = float(
            np.dot(embeddings[left["segmentId"]], embeddings[right["segmentId"]])
        )
        pairs.append(
            {
                "left": left["segmentId"],
                "right": right["segmentId"],
                "cosineSimilarity": round(similarity, 6),
            }
        )
    mean_scores = {}
    for item in records:
        relevant = [
            pair["cosineSimilarity"]
            for pair in pairs
            if item["segmentId"] in {pair["left"], pair["right"]}
        ]
        mean_scores[item["segmentId"]] = (
            sum(relevant) / len(relevant) if relevant else 1.0
        )
    medoid_id = max(mean_scores, key=mean_scores.get)
    minimum_consistency = float(job.get("minimumConsistency", 0.72))
    accepted = [
        item["segmentId"]
        for item in records
        if mean_scores[item["segmentId"]] >= minimum_consistency
    ]
    clone_samples = []
    medoid_embedding = embeddings[medoid_id]
    for sample in job.get("cloneSamples", []):
        similarity = float(np.dot(medoid_embedding, embedding(sample["path"])))
        clone_samples.append(
            {
                **sample,
                "cosineSimilarity": round(similarity, 6),
                "passed": similarity >= float(job.get("minimumCloneSimilarity", 0.80)),
            }
        )
    report = {
        "schema": "temple-ai-studio.emma-canonical-voice-consistency.v1",
        "engine": "microsoft-wavlm-base-plus-sv",
        "modelPath": str(model_path),
        "device": device,
        "pairwise": pairs,
        "meanSimilarity": {
            key: round(value, 6) for key, value in mean_scores.items()
        },
        "medoidSegmentId": medoid_id,
        "acceptedSegmentIds": accepted,
        "minimumConsistency": minimum_consistency,
        "cloneSamples": clone_samples,
        "overall": "PASS"
        if len(accepted) >= max(1, len(records) - 1)
        and all(item["passed"] for item in clone_samples)
        else "FAIL",
    }
    atomic_json(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
