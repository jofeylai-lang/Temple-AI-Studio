from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class EvaluatorUnavailableError(RuntimeError):
    pass


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("Embedding vectors must be non-empty and have matching dimensions.")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


class OpenCVSFaceEvaluator:
    """Commercial-friendly face similarity using OpenCV Zoo YuNet + SFace."""

    def __init__(self, detector_model: Path, recognition_model: Path):
        self.detector_model = Path(detector_model).resolve()
        self.recognition_model = Path(recognition_model).resolve()

    def health(self) -> dict[str, Any]:
        checks = [
            {"name": "detector-model", "ok": self.detector_model.is_file(), "path": str(self.detector_model)},
            {"name": "recognition-model", "ok": self.recognition_model.is_file(), "path": str(self.recognition_model)},
        ]
        try:
            import cv2

            checks.append(
                {
                    "name": "opencv-sface-api",
                    "ok": hasattr(cv2, "FaceDetectorYN_create")
                    and hasattr(cv2, "FaceRecognizerSF_create"),
                    "version": cv2.__version__,
                }
            )
        except ImportError as error:
            checks.append({"name": "opencv", "ok": False, "reason": str(error)})
        return {"overall": "PASS" if all(item["ok"] for item in checks) else "FAIL", "checks": checks}

    def embedding(self, image_path: Path) -> list[float]:
        health = self.health()
        if health["overall"] != "PASS":
            raise EvaluatorUnavailableError(f"OpenCV SFace evaluator is unavailable: {health}")
        import cv2

        image = cv2.imread(str(Path(image_path)))
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")
        height, width = image.shape[:2]
        detector = cv2.FaceDetectorYN_create(
            str(self.detector_model),
            "",
            (width, height),
            0.9,
            0.3,
            5000,
        )
        recognizer = cv2.FaceRecognizerSF_create(str(self.recognition_model), "")
        _, faces = detector.detect(image)
        if faces is None or len(faces) != 1:
            raise ValueError(
                f"Exactly one clearly detected face is required; detected {0 if faces is None else len(faces)}."
            )
        aligned = recognizer.alignCrop(image, faces[0])
        feature = recognizer.feature(aligned)
        return [float(value) for value in feature.flatten()]

    def compare(self, reference: Path, candidate: Path, threshold: float = 0.363) -> dict[str, Any]:
        left = self.embedding(reference)
        right = self.embedding(candidate)
        score = cosine_similarity(left, right)
        return {
            "schema": "temple-ai-studio.identity-similarity.opencv-sface.v1",
            "evaluator": "opencv-sface",
            "provenance": "real-production",
            "reference": str(Path(reference).resolve()),
            "candidate": str(Path(candidate).resolve()),
            "score": round(score, 6),
            "threshold": threshold,
            "passed": score >= threshold,
        }


class WavLMSpeakerEvaluator:
    """Speaker similarity using Microsoft's WavLM speaker-verification model."""

    def __init__(self, python_model_path: Path | str):
        self.model_path = str(python_model_path)
        self._processor = None
        self._model = None

    def health(self) -> dict[str, Any]:
        checks = []
        model_path = Path(self.model_path)
        checks.append(
            {
                "name": "model",
                "ok": model_path.is_dir(),
                "path": str(model_path.resolve()) if model_path.exists() else str(model_path),
            }
        )
        try:
            import soundfile
            import torch
            import transformers

            checks.append(
                {
                    "name": "runtime",
                    "ok": True,
                    "transformers": transformers.__version__,
                    "torch": torch.__version__,
                    "soundfile": soundfile.__version__,
                }
            )
        except ImportError as error:
            checks.append({"name": "runtime", "ok": False, "reason": str(error)})
        return {"overall": "PASS" if all(item["ok"] for item in checks) else "FAIL", "checks": checks}

    def _load(self) -> None:
        if self._model is not None:
            return
        health = self.health()
        if health["overall"] != "PASS":
            raise EvaluatorUnavailableError(f"WavLM evaluator is unavailable: {health}")
        from transformers import AutoFeatureExtractor, AutoModelForAudioXVector

        self._processor = AutoFeatureExtractor.from_pretrained(
            self.model_path,
            local_files_only=True,
        )
        self._model = AutoModelForAudioXVector.from_pretrained(
            self.model_path,
            local_files_only=True,
        )
        self._model.eval()

    def embedding(self, audio_path: Path) -> list[float]:
        self._load()
        import soundfile as sf
        import torch

        samples, sample_rate = sf.read(str(Path(audio_path)), dtype="float32")
        if getattr(samples, "ndim", 1) > 1:
            samples = samples.mean(axis=1)
        inputs = self._processor(
            samples,
            sampling_rate=sample_rate,
            return_tensors="pt",
        )
        with torch.inference_mode():
            outputs = self._model(**inputs)
        embeddings = outputs.embeddings
        embeddings = torch.nn.functional.normalize(embeddings, dim=-1)
        return [float(value) for value in embeddings[0].cpu().tolist()]

    def compare(self, reference: Path, candidate: Path, threshold: float = 0.80) -> dict[str, Any]:
        score = cosine_similarity(self.embedding(reference), self.embedding(candidate))
        return {
            "schema": "temple-ai-studio.voice-similarity.wavlm.v1",
            "evaluator": "wavlm-base-plus-sv",
            "provenance": "real-production",
            "reference": str(Path(reference).resolve()),
            "candidate": str(Path(candidate).resolve()),
            "score": round(score, 6),
            "threshold": threshold,
            "passed": score >= threshold,
        }


def write_validation_evidence(
    path: Path,
    identity_results: list[dict[str, Any]],
    voice_results: list[dict[str, Any]],
    body_consistency: float,
    voice_naturalness: float,
    commercial_usability: float,
) -> dict[str, Any]:
    if not identity_results or not voice_results:
        raise ValueError("Real identity and voice evaluations are required.")
    identity_score = min(item["score"] for item in identity_results)
    voice_score = min(item["score"] for item in voice_results)
    checks = {
        "identitySimilarity": {"score": identity_score, "passed": identity_score >= 0.363},
        "bodyConsistency": {"score": body_consistency, "passed": body_consistency >= 0.78},
        "voiceSimilarity": {"score": voice_score, "passed": voice_score >= 0.80},
        "voiceNaturalness": {"score": voice_naturalness, "passed": voice_naturalness >= 0.80},
        "commercialUsability": {
            "score": commercial_usability,
            "passed": commercial_usability >= 0.80,
        },
    }
    payload = {
        "schema": "temple-ai-studio.emma-production-validation-evidence.v1",
        "provenance": "real-production",
        "identityEvaluator": "opencv-sface",
        "voiceEvaluator": "wavlm-base-plus-sv",
        "checks": checks,
        "identityResults": identity_results,
        "voiceResults": voice_results,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
