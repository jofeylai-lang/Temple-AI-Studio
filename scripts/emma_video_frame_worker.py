from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any

import cv2
import numpy as np

from emma_quality_worker import (
    detect_faces,
    detector_for,
    face_feature,
    geometry,
    hair_hsv,
    hsv_similarity,
    primary_face,
    primary_faces,
    skin_texture,
)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def difference_hash(image: np.ndarray, size: int = 8) -> str:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = resized[:, :-1] > resized[:, 1:]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def blockiness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    vertical = np.abs(gray[:, 1:] - gray[:, :-1])
    horizontal = np.abs(gray[1:, :] - gray[:-1, :])
    boundary = np.concatenate(
        [
            vertical[:, 7::8].reshape(-1),
            horizontal[7::8, :].reshape(-1),
        ]
    )
    regular = np.concatenate(
        [
            vertical[:, 3::8].reshape(-1),
            horizontal[3::8, :].reshape(-1),
        ]
    )
    if not len(boundary) or not len(regular):
        return 0.0
    return float(np.mean(boundary) / max(np.mean(regular), 0.1))


def subtitle_obstruction(image: np.ndarray) -> dict[str, Any]:
    height, width = image.shape[:2]
    lower = image[int(height * 0.78) :, :]
    gray = cv2.cvtColor(lower, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 220)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    text_like = 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if 3 <= h <= max(8, lower.shape[0] // 5) and 2 <= w <= width // 3:
            text_like += 1
    density = float(np.count_nonzero(edges) / max(1, edges.size))
    obstructed = density > 0.24 and text_like >= 35
    return {
        "ok": not obstructed,
        "edgeDensity": round(density, 5),
        "textLikeComponents": text_like,
    }


def scene_distance(previous: np.ndarray | None, image: np.ndarray) -> float:
    small = cv2.resize(image, (160, 90), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    histogram = cv2.calcHist([hsv], [0, 1], None, [24, 24], [0, 180, 0, 256])
    cv2.normalize(histogram, histogram)
    if previous is None:
        return 1.0
    return float(cv2.compareHist(previous, histogram, cv2.HISTCMP_BHATTACHARYYA))


def histogram_for(image: np.ndarray) -> np.ndarray:
    small = cv2.resize(image, (160, 90), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    histogram = cv2.calcHist([hsv], [0, 1], None, [24, 24], [0, 180, 0, 256])
    cv2.normalize(histogram, histogram)
    return histogram


def face_landmarker(path: str) -> Any:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    return vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=path),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=True,
            min_face_detection_confidence=0.45,
            min_face_presence_confidence=0.45,
            min_tracking_confidence=0.45,
        )
    )


def blendshape_checks(model: Any, image: np.ndarray) -> dict[str, Any]:
    import mediapipe as mp

    media = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
    )
    result = model.detect(media)
    if not result.face_blendshapes:
        return {
            "ok": False,
            "reason": "face-landmarks-not-detected",
            "closedEyeFailure": True,
        }
    scores = {
        item.category_name: float(item.score)
        for item in result.face_blendshapes[0]
    }
    left = scores.get("eyeBlinkLeft", 0.0)
    right = scores.get("eyeBlinkRight", 0.0)
    closed = (left + right) / 2 >= 0.58 or min(left, right) >= 0.48
    smile = max(scores.get("mouthSmileLeft", 0.0), scores.get("mouthSmileRight", 0.0))
    jaw = scores.get("jawOpen", 0.0)
    return {
        "ok": not closed,
        "closedEyeFailure": closed,
        "eyeBlinkLeft": round(left, 4),
        "eyeBlinkRight": round(right, 4),
        "smile": round(smile, 4),
        "jawOpen": round(jaw, 4),
    }


def classify(face: np.ndarray, image: np.ndarray, expression: dict[str, Any]) -> tuple[str, list[str]]:
    height, width = image.shape[:2]
    face_ratio = float(face[3] / max(height, 1))
    points = face[4:14].reshape(5, 2)
    nose_position = float((points[2][0] - face[0]) / max(face[2], 1))
    profile = abs(nose_position - 0.5) >= 0.14
    tags = []
    if face_ratio >= 0.29:
        category = "close_up"
        tags.append("face-close-up")
    elif face_ratio >= 0.145:
        category = "upper_body"
        tags.append("upper-body")
    else:
        category = "full_body"
        tags.append("full-body")
    if profile:
        tags.append("profile")
    if expression.get("smile", 0.0) >= 0.38 or expression.get("jawOpen", 0.0) >= 0.32:
        tags.append("expression")
    center_x = float((face[0] + face[2] / 2) / max(width, 1))
    if abs(center_x - 0.5) >= 0.18:
        tags.append("dynamic-composition")
    return category, tags


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and validate Emma video reference frames.")
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8-sig"))
    output_root = Path(job["outputRoot"]).resolve()
    candidate_root = output_root / "candidates"
    approved_root = output_root / "approved"
    rejected_root = output_root / "rejected"
    for path in [candidate_root, approved_root, rejected_root]:
        path.mkdir(parents=True, exist_ok=True)

    models = job["models"]
    detector = detector_for(Path(models["yunet"]))
    recognizer = cv2.FaceRecognizerSF.create(str(models["sface"]), "")
    landmark_model = face_landmarker(models["faceLandmarker"])

    anchors = []
    for raw in job["anchors"]:
        path = Path(raw)
        image = cv2.imread(str(path))
        faces = detect_faces(detector, image)
        if not len(faces):
            raise RuntimeError(f"Anchor contains no face: {path}")
        face = primary_face(faces)
        anchors.append(
            {
                "path": str(path),
                "feature": face_feature(recognizer, image, face),
                "geometry": geometry(face),
                "hair": hair_hsv(image, face),
                "texture": skin_texture(image, face),
            }
        )
    reference_geometry = np.median([item["geometry"] for item in anchors], axis=0)
    reference_hair = np.median([item["hair"] for item in anchors], axis=0)
    reference_texture = median(item["texture"] for item in anchors)
    inter_anchor = []
    for index, left in enumerate(anchors):
        for right in anchors[index + 1 :]:
            inter_anchor.append(
                float(
                    recognizer.match(
                        left["feature"],
                        right["feature"],
                        cv2.FaceRecognizerSF_FR_COSINE,
                    )
                )
            )
    identity_threshold = max(
        float(job.get("identityThreshold", 0.45)),
        max(0.40, min(inter_anchor) - 0.04),
    )
    geometry_scores = [
        max(0.0, 1.0 - float(np.mean(np.abs(item["geometry"] - reference_geometry))) / 0.12)
        for item in anchors
    ]
    geometry_threshold = max(0.45, min(geometry_scores) - 0.03)
    sample_fps = float(job.get("sampleFps", 4.0))
    candidates: list[dict[str, Any]] = []
    scene_changes: list[dict[str, Any]] = []

    for source in job["videos"]:
        video_path = Path(source["path"]).resolve()
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 24.0)
        interval = max(1, round(fps / sample_fps))
        frame_index = -1
        previous_histogram = None
        last_sample = -interval
        while True:
            ok, image = capture.read()
            if not ok:
                break
            frame_index += 1
            histogram = histogram_for(image)
            distance = (
                1.0
                if previous_histogram is None
                else float(
                    cv2.compareHist(
                        previous_histogram,
                        histogram,
                        cv2.HISTCMP_BHATTACHARYYA,
                    )
                )
            )
            scene_cut = frame_index == 0 or distance >= float(job.get("sceneThreshold", 0.33))
            previous_histogram = histogram
            if not scene_cut and frame_index - last_sample < interval:
                continue
            last_sample = frame_index
            timestamp = frame_index / fps
            if scene_cut:
                scene_changes.append(
                    {
                        "sourceId": source["id"],
                        "frame": frame_index,
                        "timestampSeconds": round(timestamp, 3),
                        "distance": round(distance, 5),
                    }
                )
            name = f"{source['id']}_{frame_index:05d}_{round(timestamp * 1000):07d}ms.jpg"
            candidate_path = candidate_root / name
            cv2.imwrite(str(candidate_path), image, [cv2.IMWRITE_JPEG_QUALITY, 96])
            height, width = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            faces = primary_faces(detect_faces(detector, image))
            reasons = []
            checks: dict[str, Any] = {
                "resolution": {
                    "ok": min(width, height) >= 1000 and width * height >= 1_900_000,
                    "width": width,
                    "height": height,
                },
                "sharpness": {"ok": blur_score >= 75.0, "laplacianVariance": round(blur_score, 3)},
            }
            if not checks["resolution"]["ok"]:
                reasons.append("low-resolution")
            if not checks["sharpness"]["ok"]:
                reasons.append("blur")
            if len(faces) != 1:
                reasons.append("face-count")
                candidates.append(
                    {
                        "path": str(candidate_path),
                        "sourceId": source["id"],
                        "sourcePath": str(video_path),
                        "sourceSha256": source["sha256"],
                        "frame": frame_index,
                        "timestampSeconds": round(timestamp, 3),
                        "sceneCut": scene_cut,
                        "category": "unclassified",
                        "tags": [],
                        "overall": "REJECT",
                        "reasons": reasons,
                        "checks": checks | {"faceCount": {"ok": False, "count": len(faces)}},
                        "score": 0.0,
                        "differenceHash": difference_hash(image),
                    }
                )
                continue

            face = primary_face(faces)
            feature = face_feature(recognizer, image, face)
            similarities = [
                float(
                    recognizer.match(
                        feature,
                        anchor["feature"],
                        cv2.FaceRecognizerSF_FR_COSINE,
                    )
                )
                for anchor in anchors
            ]
            anchor_passes = sum(value >= identity_threshold for value in similarities)
            identity_ok = anchor_passes >= int(job.get("minimumAnchorPasses", 3))
            checks["identity"] = {
                "ok": identity_ok,
                "threshold": round(identity_threshold, 5),
                "anchorPasses": anchor_passes,
                "similarities": [round(value, 5) for value in similarities],
                "mean": round(float(np.mean(similarities)), 5),
            }
            if not identity_ok:
                reasons.append("identity-drift")

            geometry_score = max(
                0.0,
                1.0
                - float(np.mean(np.abs(geometry(face) - reference_geometry))) / 0.12,
            )
            geometry_ok = geometry_score >= geometry_threshold
            checks["facialGeometry"] = {
                "ok": geometry_ok,
                "score": round(geometry_score, 5),
                "threshold": round(geometry_threshold, 5),
            }
            if not geometry_ok:
                reasons.append("facial-geometry-drift")

            hair_score = hsv_similarity(hair_hsv(image, face), reference_hair)
            hair_ok = hair_score >= 0.58
            checks["hair"] = {"ok": hair_ok, "score": round(hair_score, 5)}
            if not hair_ok:
                reasons.append("hair-color-drift")

            texture = skin_texture(image, face)
            texture_floor = max(12.0, reference_texture * 0.24)
            texture_ok = texture >= texture_floor
            checks["skinTexture"] = {
                "ok": texture_ok,
                "laplacianVariance": round(texture, 3),
                "minimum": round(texture_floor, 3),
            }
            if not texture_ok:
                reasons.append("over-smoothed-skin")

            expression = blendshape_checks(landmark_model, image)
            checks["eyesAndExpression"] = expression
            if not expression["ok"]:
                reasons.append("closed-eye-or-face-landmark-failure")
            category, tags = classify(face, image, expression)

            obstruction = subtitle_obstruction(image)
            checks["subtitleWatermark"] = obstruction
            if not obstruction["ok"]:
                reasons.append("subtitle-or-watermark-obstruction")

            compression = blockiness(image)
            compression_ok = compression <= 1.85
            checks["compression"] = {
                "ok": compression_ok,
                "blockBoundaryRatio": round(compression, 5),
            }
            if not compression_ok:
                reasons.append("compression-artifacts")

            face_ratio = float(face[3] / height)
            proportion_ok = 0.07 <= face_ratio <= 0.72
            checks["bodyProportion"] = {
                "ok": proportion_ok,
                "faceHeightRatio": round(face_ratio, 5),
            }
            if not proportion_ok:
                reasons.append("body-proportion-drift")

            components = [
                min(1.0, max(0.0, (float(np.mean(similarities)) + 0.1) / 0.75)),
                geometry_score,
                hair_score,
                min(1.0, texture / max(reference_texture, 1.0)),
                min(1.0, blur_score / 220.0),
                1.0 if obstruction["ok"] else 0.3,
                1.0 if compression_ok else 0.3,
                1.0 if expression["ok"] else 0.3,
            ]
            candidates.append(
                {
                    "path": str(candidate_path),
                    "sourceId": source["id"],
                    "sourcePath": str(video_path),
                    "sourceSha256": source["sha256"],
                    "frame": frame_index,
                    "timestampSeconds": round(timestamp, 3),
                    "sceneCut": scene_cut,
                    "category": category,
                    "tags": tags,
                    "overall": "PASS" if not reasons else "REJECT",
                    "reasons": reasons,
                    "checks": checks,
                    "score": round(sum(components) / len(components), 5),
                    "differenceHash": difference_hash(image),
                }
            )
        capture.release()

    accepted: list[dict[str, Any]] = []
    known_hashes: list[str] = []
    per_source: dict[str, int] = {}
    last_timestamp: dict[str, float] = {}
    for item in sorted(candidates, key=lambda record: record["score"], reverse=True):
        if item["overall"] != "PASS":
            continue
        source_id = item["sourceId"]
        if per_source.get(source_id, 0) >= int(job.get("maximumFramesPerVideo", 8)):
            item["overall"] = "REJECT"
            item["reasons"].append("per-video-limit")
            continue
        previous_time = last_timestamp.get(source_id)
        if previous_time is not None and abs(item["timestampSeconds"] - previous_time) < 0.45:
            item["overall"] = "REJECT"
            item["reasons"].append("nearby-redundant-frame")
            continue
        if any(hamming(item["differenceHash"], known) <= 4 for known in known_hashes):
            item["overall"] = "REJECT"
            item["reasons"].append("perceptual-duplicate")
            continue
        source = Path(item["path"])
        target = approved_root / source.name
        if not target.exists():
            target.write_bytes(source.read_bytes())
        item["approvedPath"] = str(target)
        item["approvedSha256"] = sha256_file(target)
        accepted.append(item)
        known_hashes.append(item["differenceHash"])
        per_source[source_id] = per_source.get(source_id, 0) + 1
        last_timestamp[source_id] = item["timestampSeconds"]

    for item in candidates:
        if item["overall"] == "PASS" and "approvedPath" not in item:
            item["overall"] = "REJECT"
            item["reasons"].append("selection-filter")
        if item["overall"] == "REJECT":
            source = Path(item["path"])
            metadata = rejected_root / f"{source.name}.json"
            atomic_json(metadata, item)

    report = {
        "schema": "temple-ai-studio.emma-video-frame-activation.v1",
        "identityEvaluator": "opencv-sface",
        "faceLandmarker": "mediapipe-face-landmarker",
        "identityThreshold": round(identity_threshold, 5),
        "minimumAnchorPasses": int(job.get("minimumAnchorPasses", 3)),
        "anchorCalibration": {
            "minimumInterAnchorSimilarity": round(min(inter_anchor), 5),
            "medianInterAnchorSimilarity": round(median(inter_anchor), 5),
        },
        "sceneChanges": scene_changes,
        "approved": accepted,
        "candidates": candidates,
        "summary": {
            "sourceVideos": len(job["videos"]),
            "candidateFrames": len(candidates),
            "approvedFrames": len(accepted),
            "rejectedFrames": len(candidates) - len(accepted),
            "approvedBySource": per_source,
            "coverageTags": sorted({tag for item in accepted for tag in item["tags"]}),
        },
        "overall": "PASS" if accepted else "FAIL",
    }
    atomic_json(Path(args.output), report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if report["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
