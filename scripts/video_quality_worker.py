from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_openclip(path: Path, device: str) -> tuple[Any, Any, Any, str]:
    import open_clip
    import torch

    selected = device if device.startswith("cuda") and torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained=str(path),
        device=selected,
    )
    model.eval()
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    text = tokenizer(
        [
            "a polished professional commercial social video frame",
            "a low quality distorted video frame with artifacts and unreadable content",
        ]
    ).to(selected)
    with torch.inference_mode():
        features = model.encode_text(text)
        features = features / features.norm(dim=-1, keepdim=True)
    return model, preprocess, features, selected


def commercial_score(
    frames: list[np.ndarray],
    model: Any,
    preprocess: Any,
    text_features: Any,
    device: str,
) -> float:
    import torch

    selected = frames[:: max(1, len(frames) // 8)][:8]
    probabilities = []
    for frame in selected:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        tensor = preprocess(image).unsqueeze(0).to(device)
        with torch.inference_mode():
            feature = model.encode_image(tensor)
            feature = feature / feature.norm(dim=-1, keepdim=True)
            probability = (100 * feature @ text_features.T).softmax(dim=-1)[0, 0]
        probabilities.append(float(probability.detach().cpu()))
    return float(np.mean(probabilities)) if probabilities else 0.0


def scene_alignment_scores(
    frames: list[np.ndarray],
    expected_scenes: int,
    model: Any,
    preprocess: Any,
    device: str,
) -> dict[str, Any]:
    import open_clip
    import torch

    labels = [
        "an engaging opening shot with a friendly lifestyle presenter in a spiritual product shop",
        "a lifestyle presenter holding up a small product inside a retail shop",
        "a close-up commercial product detail showing material texture packaging or usage",
        "a warm respectful spiritual lifestyle scene showing blessing and daily ritual",
        "a friendly presenter giving a clear commercial call to action",
        "a polished warm brand closing shot with a friendly presenter",
    ]
    negatives = [
        "a blank static filler frame with no engaging opening or presenter",
        "a person posing in a plain location without holding or presenting an item",
        "a full body fashion portrait of a person with no visible product close-up",
        "a cold corporate office fashion runway scene with no warm spiritual shop setting",
        "an empty shelf or product image with no presenter invitation",
        "an unfinished middle scene with no clear closing presenter or brand feeling",
    ]
    segment_count = max(1, min(expected_scenes, len(frames), len(labels)))
    indices = [
        min(len(frames) - 1, round((index + 0.5) * len(frames) / segment_count))
        for index in range(segment_count)
    ]
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    scores = []
    for index, frame_index in enumerate(indices):
        text = tokenizer([labels[index], negatives[index]]).to(device)
        image = Image.fromarray(cv2.cvtColor(frames[frame_index], cv2.COLOR_BGR2RGB))
        tensor = preprocess(image).unsqueeze(0).to(device)
        with torch.inference_mode():
            text_features = model.encode_text(text)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            image_feature = model.encode_image(tensor)
            image_feature = image_feature / image_feature.norm(dim=-1, keepdim=True)
            probability = (100 * image_feature @ text_features.T).softmax(dim=-1)[0, 0]
        scores.append(
            {
                "scene": index + 1,
                "label": labels[index],
                "score": round(float(probability.detach().cpu()), 5),
            }
        )
    values = [item["score"] for item in scores]
    return {
        "average": round(float(np.mean(values)), 5) if values else 0.0,
        "minimum": round(float(np.min(values)), 5) if values else 0.0,
        "scenes": scores,
    }


def extract_audio(ffmpeg: Path, video: Path, output: Path) -> bool:
    result = subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-v",
            "error",
            "-i",
            str(video),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    return result.returncode == 0 and output.is_file() and output.stat().st_size > 44


def read_video(path: Path) -> tuple[list[np.ndarray], dict[str, Any]]:
    capture = cv2.VideoCapture(str(path))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frames = []
    stride = max(1, frame_count // 180)
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % stride == 0:
            frames.append(frame)
        index += 1
    capture.release()
    return frames, {
        "fps": round(fps, 3),
        "frameCount": frame_count,
        "width": width,
        "height": height,
        "durationSeconds": round(frame_count / fps, 3) if fps else 0.0,
    }


def motion_metrics(frames: list[np.ndarray]) -> dict[str, Any]:
    if len(frames) < 2:
        return {
            "motionScore": 0.0,
            "freezeRatio": 1.0,
            "cameraStability": 0.0,
            "cameraJitterScore": 0.0,
            "motionSmoothness": 0.0,
        }
    motion = []
    shifts = []
    previous = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    previous = cv2.resize(previous, (256, 256))
    for frame in frames[1:]:
        current = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (256, 256))
        motion.append(float(np.mean(cv2.absdiff(current, previous)) / 255))
        shift, _ = cv2.phaseCorrelate(previous.astype(np.float32), current.astype(np.float32))
        shifts.append(float(np.hypot(shift[0], shift[1])))
        previous = current
    shift_array = np.asarray(shifts, dtype=np.float32)
    acceleration = np.abs(np.diff(shift_array)) if len(shift_array) > 1 else np.asarray([12.0])
    jitter_level = float(np.percentile(acceleration, 90))
    jitter_score = max(0.0, 1.0 - jitter_level / 4.0)
    return {
        "motionScore": round(float(np.mean(motion)), 5),
        "freezeRatio": round(float(np.mean(np.asarray(motion) < 0.0015)), 5),
        "cameraStability": round(max(0.0, 1.0 - float(np.median(shifts)) / 12.0), 5),
        "cameraJitterScore": round(jitter_score, 5),
        "motionSmoothness": round(jitter_score, 5),
        "shiftAccelerationP90": round(jitter_level, 5),
    }


def difference_hash(frame: np.ndarray) -> np.ndarray:
    content = frame[: max(1, int(frame.shape[0] * 0.72)), :]
    gray = cv2.cvtColor(content, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (17, 16), interpolation=cv2.INTER_AREA)
    return (resized[:, 1:] > resized[:, :-1]).reshape(-1)


def hamming_distance(left: np.ndarray, right: np.ndarray) -> int:
    return int(np.count_nonzero(left != right))


def cluster_hashes(hashes: list[np.ndarray], threshold: int = 18) -> list[list[int]]:
    clusters: list[list[int]] = []
    representatives: list[np.ndarray] = []
    for index, value in enumerate(hashes):
        match = next(
            (
                cluster_index
                for cluster_index, representative in enumerate(representatives)
                if hamming_distance(value, representative) <= threshold
            ),
            None,
        )
        if match is None:
            representatives.append(value)
            clusters.append([index])
        else:
            clusters[match].append(index)
    return clusters


def visual_diversity_metrics(frames: list[np.ndarray], expected_scenes: int) -> dict[str, Any]:
    if not frames:
        return {
            "uniqueSceneEstimate": 0,
            "repeatedFrameRatio": 1.0,
            "repeatedAssetRatio": 1.0,
            "visualDiversity": 0.0,
        }
    hashes = [difference_hash(frame) for frame in frames]
    adjacent = [
        hamming_distance(left, right)
        for left, right in zip(hashes, hashes[1:])
    ]
    repeated_frames = float(np.mean(np.asarray(adjacent) <= 2)) if adjacent else 1.0
    segment_count = max(1, min(expected_scenes, len(frames)))
    segment_indices = [
        min(len(frames) - 1, round((index + 0.5) * len(frames) / segment_count))
        for index in range(segment_count)
    ]
    segment_hashes = [hashes[index] for index in segment_indices]
    hash_clusters = cluster_hashes(segment_hashes)
    segment_images = [
        cv2.resize(
            frames[index][: max(1, int(frames[index].shape[0] * 0.72)), :],
            (64, 96),
            interpolation=cv2.INTER_AREA,
        )
        for index in segment_indices
    ]
    clusters: list[list[int]] = []
    representatives: list[np.ndarray] = []
    for index, value in enumerate(segment_images):
        match = next(
            (
                cluster_index
                for cluster_index, representative in enumerate(representatives)
                if float(np.mean(cv2.absdiff(value, representative)) / 255) <= 0.13
            ),
            None,
        )
        if match is None:
            representatives.append(value)
            clusters.append([index])
        else:
            clusters[match].append(index)
    largest_cluster = max((len(cluster) for cluster in clusters), default=segment_count)
    return {
        "uniqueSceneEstimate": len(clusters),
        "perceptualHashSceneEstimate": len(hash_clusters),
        "repeatedFrameRatio": round(repeated_frames, 5),
        "repeatedAssetRatio": round(largest_cluster / max(1, segment_count), 5),
        "visualDiversity": round(len(clusters) / max(1, segment_count), 5),
        "sampledSceneCount": segment_count,
        "segmentFrameIndices": segment_indices,
    }


def mouth_motion(
    frames: list[np.ndarray],
    detector_model: Path,
) -> list[float]:
    detector = cv2.FaceDetectorYN.create(str(detector_model), "", (320, 320), 0.5, 0.3, 5000)
    crops = []
    for frame in frames:
        height, width = frame.shape[:2]
        detector.setInputSize((width, height))
        faces = detector.detect(frame)[1]
        if faces is None or not len(faces):
            crops.append(None)
            continue
        face = faces[int(np.argmax(faces[:, 2] * faces[:, 3]))]
        x, y, face_width, face_height = [int(value) for value in face[:4]]
        x1 = max(0, x + int(face_width * 0.18))
        x2 = min(width, x + int(face_width * 0.82))
        y1 = max(0, y + int(face_height * 0.56))
        y2 = min(height, y + int(face_height * 0.92))
        crop = frame[y1:y2, x1:x2]
        crops.append(cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (96, 48)) if crop.size else None)
    result = [0.0]
    for previous, current in zip(crops, crops[1:]):
        if previous is None or current is None:
            result.append(0.0)
        else:
            result.append(float(np.mean(cv2.absdiff(previous, current)) / 255))
    return result


def sync_proxy(
    mouth: list[float],
    audio_path: Path,
    fps: float,
) -> dict[str, Any]:
    import soundfile as sf

    audio, sample_rate = sf.read(str(audio_path), always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    samples_per_frame = max(1, round(sample_rate / max(fps, 1)))
    energy = []
    for index in range(len(mouth)):
        segment = audio[index * samples_per_frame : (index + 1) * samples_per_frame]
        energy.append(float(np.sqrt(np.mean(np.square(segment)))) if len(segment) else 0.0)
    mouth_array = np.asarray(mouth, dtype=np.float32)
    energy_array = np.asarray(energy, dtype=np.float32)
    if np.std(mouth_array) < 1e-7 or np.std(energy_array) < 1e-7:
        return {"correlation": 0.0, "offsetFrames": 0, "passed": False}
    best = (-1.0, 0)
    for offset in range(-5, 6):
        shifted = np.roll(energy_array, offset)
        correlation = float(np.corrcoef(mouth_array, shifted)[0, 1])
        if np.isfinite(correlation) and correlation > best[0]:
            best = (correlation, offset)
    return {
        "correlation": round(best[0], 5),
        "offsetFrames": best[1],
        "passed": best[0] >= 0.12 and abs(best[1]) <= 4,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio local video quality evaluator.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--syncnet", default="")
    parser.add_argument("--openclip", default="")
    parser.add_argument("--yunet", default="")
    parser.add_argument("--expected-scenes", type=int, default=6)
    parser.add_argument("--editorial-only", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    video = Path(args.video).resolve()
    ffmpeg = Path(args.ffmpeg).resolve()
    syncnet = Path(args.syncnet).resolve()
    openclip = Path(args.openclip).resolve()
    yunet = Path(args.yunet).resolve()
    required_paths = [video, ffmpeg]
    if not args.editorial_only:
        required_paths.extend([syncnet, openclip, yunet])
    for required in required_paths:
        if not required.is_file():
            raise FileNotFoundError(str(required))

    frames, media = read_video(video)
    motion = motion_metrics(frames)
    diversity = visual_diversity_metrics(frames, max(1, args.expected_scenes))
    if args.editorial_only:
        syncnet_loaded = False
        if openclip.is_file():
            model, preprocess, text_features, device = load_openclip(openclip, "cuda:0")
            visual_score = commercial_score(frames, model, preprocess, text_features, device)
            alignment = scene_alignment_scores(
                frames,
                max(1, args.expected_scenes),
                model,
                preprocess,
                device,
            )
        else:
            device = "not-loaded"
            visual_score = 0.0
            alignment = {"average": 0.0, "minimum": 0.0, "scenes": []}
        audio_available = False
        synchronization = {"correlation": 0.0, "offsetFrames": 0, "passed": False}
    else:
        import torch

        syncnet_payload = torch.load(str(syncnet), map_location="cpu", weights_only=False)
        syncnet_loaded = isinstance(syncnet_payload, dict) and bool(syncnet_payload)
        model, preprocess, text_features, device = load_openclip(openclip, "cuda:0")
        visual_score = commercial_score(frames, model, preprocess, text_features, device)
        alignment = scene_alignment_scores(
            frames,
            max(1, args.expected_scenes),
            model,
            preprocess,
            device,
        )
        with tempfile.TemporaryDirectory() as temporary:
            audio_path = Path(temporary) / "audio.wav"
            audio_available = extract_audio(ffmpeg, video, audio_path)
            synchronization = (
                sync_proxy(mouth_motion(frames, yunet), audio_path, media["fps"])
                if audio_available
                else {"correlation": 0.0, "offsetFrames": 0, "passed": False}
            )
    checks = {
        "playback": len(frames) >= 2 and media["durationSeconds"] > 0,
        "resolution": media["width"] >= 720 and media["height"] >= 720,
        "frameRate": 23 <= media["fps"] <= 60,
        "motion": motion["freezeRatio"] < 0.98,
        "cameraStability": motion["cameraStability"] >= 0.45,
        "cameraJitter": motion["cameraJitterScore"] >= 0.65,
        "motionSmoothness": motion["motionSmoothness"] >= 0.65,
        "repeatedFrames": diversity["repeatedFrameRatio"] < 0.75,
        "repeatedAssets": diversity["repeatedAssetRatio"] <= 0.40,
        "visualDiversity": diversity["visualDiversity"] >= 0.65,
        "meaningfulScenes": diversity["uniqueSceneEstimate"] >= min(5, args.expected_scenes),
    }
    if openclip.is_file():
        checks.update(
            {
                "commercialVisual": visual_score >= 0.55,
                "sceneToScriptAlignment": alignment["average"] >= 0.55
                and alignment["minimum"] >= 0.35,
            }
        )
    if not args.editorial_only:
        checks.update(
            {
                "audio": audio_available,
                "lipAudioSync": synchronization["passed"],
                "commercialVisual": visual_score >= 0.55,
                "syncNetModel": syncnet_loaded,
            }
        )
    report = {
        "schema": "temple-ai-studio.video-quality-local.v1",
        "overall": "PASS" if all(checks.values()) else "FAIL",
        "provenance": "real-production",
        "video": str(video),
        "media": media,
        "motion": motion,
        "editorial": diversity,
        "synchronization": synchronization,
        "commercialVisualScore": round(visual_score, 5),
        "sceneToScriptAlignment": alignment,
        "models": (
            {
                "syncNet": {"path": str(syncnet), "sha256": sha256_file(syncnet), "loaded": syncnet_loaded},
                "openClip": {"path": str(openclip), "device": device},
                "yuNet": str(yunet),
            }
            if not args.editorial_only
            else {"mode": "editorial-only", "device": device}
        ),
        "checks": checks,
    }
    atomic_json(Path(args.output).resolve(), report)
    print(json.dumps({"overall": report["overall"], "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
