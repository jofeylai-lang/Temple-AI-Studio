from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path
from statistics import median
from typing import Any

import cv2
import numpy as np
from PIL import Image


COCO_LIMBS = (
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
)
MEDIAPIPE_LIMBS = (
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (23, 25),
    (25, 27),
    (24, 26),
    (26, 28),
)


def install_xtcoco_compatibility() -> None:
    try:
        import xtcocotools  # noqa: F401

        return
    except ImportError:
        import pycocotools
        import pycocotools._mask
        import pycocotools.coco
        import pycocotools.cocoeval
        import pycocotools.mask

        sys.modules["xtcocotools"] = pycocotools
        sys.modules["xtcocotools._mask"] = pycocotools._mask
        sys.modules["xtcocotools.coco"] = pycocotools.coco
        sys.modules["xtcocotools.cocoeval"] = pycocotools.cocoeval
        sys.modules["xtcocotools.mask"] = pycocotools.mask
        version = types.ModuleType("xtcocotools.version")
        version.__version__ = "pycocotools-compatible"
        sys.modules["xtcocotools.version"] = version


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def detector_for(path: Path) -> Any:
    return cv2.FaceDetectorYN.create(str(path), "", (320, 320), 0.30, 0.3, 5000)


def detect_faces(detector: Any, image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    detector.setInputSize((width, height))
    detected = detector.detect(image)[1]
    if detected is None:
        return np.empty((0, 15), dtype=np.float32)
    return detected


def primary_faces(faces: np.ndarray) -> np.ndarray:
    if not len(faces):
        return faces
    areas = faces[:, 2] * faces[:, 3]
    largest = float(np.max(areas))
    significant = faces[(areas >= largest * 0.22) & (faces[:, -1] >= 0.50)]
    return significant if len(significant) else faces[[int(np.argmax(areas))]]


def primary_face(faces: np.ndarray) -> np.ndarray:
    return faces[int(np.argmax(faces[:, 2] * faces[:, 3]))]


def face_feature(recognizer: Any, image: np.ndarray, face: np.ndarray) -> np.ndarray:
    aligned = recognizer.alignCrop(image, face)
    return recognizer.feature(aligned)


def geometry(face: np.ndarray) -> np.ndarray:
    x, y, width, height = face[:4]
    points = face[4:14].reshape(5, 2)
    left_eye, right_eye, nose, left_mouth, right_mouth = points
    scale = max(width, height, 1.0)
    return np.asarray(
        [
            np.linalg.norm(left_eye - right_eye) / scale,
            np.linalg.norm(left_mouth - right_mouth) / scale,
            (nose[1] - min(left_eye[1], right_eye[1])) / scale,
            (max(left_mouth[1], right_mouth[1]) - nose[1]) / scale,
            (nose[0] - x) / max(width, 1.0),
            (nose[1] - y) / max(height, 1.0),
        ],
        dtype=np.float32,
    )


def crop_face(image: np.ndarray, face: np.ndarray) -> np.ndarray:
    x, y, width, height = [int(value) for value in face[:4]]
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(image.shape[1], x + width)
    y2 = min(image.shape[0], y + height)
    return image[y1:y2, x1:x2]


def hair_hsv(image: np.ndarray, face: np.ndarray) -> np.ndarray:
    x, y, width, height = [int(value) for value in face[:4]]
    x1 = max(0, x - width // 5)
    x2 = min(image.shape[1], x + width + width // 5)
    y1 = max(0, y - height // 3)
    y2 = min(image.shape[0], y + max(3, height // 4))
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return np.zeros(3, dtype=np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    pixels = hsv.reshape(-1, 3)
    valid = pixels[(pixels[:, 1] > 35) & (pixels[:, 2] > 25) & (pixels[:, 2] < 245)]
    if not len(valid):
        valid = pixels
    return np.median(valid, axis=0).astype(np.float32)


def skin_texture(image: np.ndarray, face: np.ndarray) -> float:
    crop = crop_face(image, face)
    if crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def edge_contamination(image: np.ndarray) -> dict[str, Any]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 220)
    edge_density = float(np.count_nonzero(edges) / edges.size)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=max(60, min(image.shape[:2]) // 6),
        minLineLength=min(image.shape[:2]) // 3,
        maxLineGap=8,
    )
    long_lines = 0 if lines is None else len(lines)
    contaminated = edge_density > 0.24 or long_lines > 28
    return {
        "ok": not contaminated,
        "edgeDensity": round(edge_density, 4),
        "longLineCount": long_lines,
    }


def hsv_similarity(candidate: np.ndarray, reference: np.ndarray) -> float:
    hue_distance = min(abs(float(candidate[0] - reference[0])), 180 - abs(float(candidate[0] - reference[0])))
    saturation_distance = abs(float(candidate[1] - reference[1]))
    value_distance = abs(float(candidate[2] - reference[2]))
    distance = hue_distance / 90 * 0.55 + saturation_distance / 255 * 0.25 + value_distance / 255 * 0.2
    return max(0.0, 1.0 - distance)


def load_openclip(model_path: str, device: str) -> tuple[Any, Any, Any, Any]:
    import open_clip
    import torch

    selected_device = device if device.startswith("cuda") and torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained=model_path,
        device=selected_device,
    )
    model.eval()
    tokenizer = open_clip.get_tokenizer("ViT-B-32")
    texts = tokenizer(
        [
            "a clean professional commercial lifestyle portrait of one adult female presenter",
            "a collage or image covered with text, logos, and watermarks",
            "a low quality image with deformed anatomy and artificial plastic skin",
        ]
    ).to(selected_device)
    with torch.inference_mode():
        text_features = model.encode_text(texts)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
    return model, preprocess, text_features, selected_device


def openclip_score(
    model: Any,
    preprocess: Any,
    text_features: Any,
    device: Any,
    image_path: str,
) -> dict[str, Any]:
    import torch

    image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(device)
    with torch.inference_mode():
        image_features = model.encode_image(image)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        probabilities = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0]
    commercial = float(probabilities[0].detach().cpu())
    contamination = float(probabilities[1].detach().cpu())
    artifact = float(probabilities[2].detach().cpu())
    return {
        "commercialProbability": round(commercial, 4),
        "contaminationProbability": round(contamination, 4),
        "artifactProbability": round(artifact, 4),
    }


def mediapipe_landmarkers(pose_path: str, hand_path: str) -> tuple[Any, Any]:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    pose = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=pose_path),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.35,
            min_pose_presence_confidence=0.35,
        )
    )
    hands = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=hand_path),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=2,
            min_hand_detection_confidence=0.35,
            min_hand_presence_confidence=0.35,
        )
    )
    return pose, hands


def mediapipe_pose_result(models: tuple[Any, Any], image: np.ndarray, category: str) -> dict[str, Any]:
    import mediapipe as mp

    pose_model, hand_model = models
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    media = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    pose = pose_model.detect(media)
    hands = hand_model.detect(media)
    if not pose.pose_landmarks:
        return {"ok": False, "reason": "pose-not-detected", "score": 0.0}
    landmarks = pose.pose_landmarks[0]
    visible_indices = [
        index
        for index in range(min(33, len(landmarks)))
        if float(getattr(landmarks[index], "visibility", 1.0)) >= 0.35
    ]
    lengths = []
    for first, second in MEDIAPIPE_LIMBS:
        if first in visible_indices and second in visible_indices:
            left = np.asarray([landmarks[first].x, landmarks[first].y])
            right = np.asarray([landmarks[second].x, landmarks[second].y])
            lengths.append(float(np.linalg.norm(left - right)))
    limb_ok = True
    positive = [value for value in lengths if value > 0.005]
    if len(positive) >= 4:
        limb_ok = max(positive) / max(min(positive), 0.005) < 5.0
    hand_count = len(hands.hand_landmarks)
    hand_required = category in {"upper_body", "full_body", "poses"}
    hands_ok = hand_count >= 1 if hand_required else hand_count <= 2
    completeness = len(visible_indices) / 33
    minimum_visible = 12 if category in {"full_body", "poses"} else 8
    ok = len(visible_indices) >= minimum_visible and limb_ok and hands_ok
    return {
        "ok": ok,
        "engine": "MediaPipe Pose and Hand Landmarker",
        "visibleBodyKeypoints": len(visible_indices),
        "completeness": round(completeness, 4),
        "limbGeometryOk": limb_ok,
        "detectedHands": hand_count,
        "handsOk": hands_ok,
        "score": round(
            min(1.0, completeness / 0.55)
            * (1.0 if limb_ok else 0.55)
            * (1.0 if hands_ok else 0.55),
            4,
        ),
    }


def pose_result(model: Any, image: np.ndarray, category: str) -> dict[str, Any]:
    if model is None:
        return {"ok": False, "reason": "pose-model-unavailable", "score": 0.0}
    if isinstance(model, tuple):
        return mediapipe_pose_result(model, image, category)
    from mmpose.apis import inference_topdown

    height, width = image.shape[:2]
    sample = inference_topdown(
        model,
        image,
        bboxes=np.asarray([[0, 0, width, height]], dtype=np.float32),
    )[0]
    keypoints = np.asarray(sample.pred_instances.keypoints[0], dtype=np.float32)
    scores = np.asarray(sample.pred_instances.keypoint_scores[0], dtype=np.float32)
    body_scores = scores[:17]
    visible = body_scores >= 0.28
    required = 8 if category in {"full_body", "poses"} else 5
    completeness = float(np.count_nonzero(visible) / 17)
    limb_ratios = []
    limb_ok = True
    for first, second in COCO_LIMBS:
        if visible[first] and visible[second]:
            limb_ratios.append(float(np.linalg.norm(keypoints[first] - keypoints[second])))
    if len(limb_ratios) >= 4:
        positive = [value for value in limb_ratios if value > 1]
        if positive:
            limb_ok = max(positive) / max(min(positive), 1.0) < 5.0
    ok = int(np.count_nonzero(visible)) >= required and limb_ok
    return {
        "ok": ok,
        "visibleBodyKeypoints": int(np.count_nonzero(visible)),
        "completeness": round(completeness, 4),
        "limbGeometryOk": limb_ok,
        "score": round(min(1.0, completeness / 0.65) * (1.0 if limb_ok else 0.55), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emma synthetic identity and anatomy quality worker.")
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8-sig"))
    models = job["models"]
    detector = detector_for(Path(models["yunet"]))
    recognizer = cv2.FaceRecognizerSF.create(str(models["sface"]), "")

    anchor_records = []
    for anchor_path in job["anchors"]:
        image = cv2.imread(anchor_path)
        faces = detect_faces(detector, image)
        if not len(faces):
            raise RuntimeError(f"Identity anchor contains no detectable face: {anchor_path}")
        face = primary_face(faces)
        anchor_records.append(
            {
                "path": anchor_path,
                "feature": face_feature(recognizer, image, face),
                "geometry": geometry(face),
                "hair": hair_hsv(image, face),
                "texture": skin_texture(image, face),
            }
        )

    reference_geometry = np.median([record["geometry"] for record in anchor_records], axis=0)
    reference_hair = np.median([record["hair"] for record in anchor_records], axis=0)
    reference_texture = median(record["texture"] for record in anchor_records)
    inter_anchor = []
    for index, left in enumerate(anchor_records):
        for right in anchor_records[index + 1 :]:
            inter_anchor.append(
                float(recognizer.match(left["feature"], right["feature"], cv2.FaceRecognizerSF_FR_COSINE))
            )
    configured_threshold = float(job.get("identityThreshold", 0.45))
    calibrated_floor = max(0.40, min(inter_anchor) - 0.04) if inter_anchor else configured_threshold
    identity_threshold = max(configured_threshold, calibrated_floor)
    anchor_geometry_scores = [
        max(0.0, 1.0 - float(np.mean(np.abs(record["geometry"] - reference_geometry))) / 0.12)
        for record in anchor_records
    ]
    geometry_threshold = max(0.45, min(anchor_geometry_scores) - 0.03)

    pose_model = None
    pose_error = ""
    try:
        install_xtcoco_compatibility()
        from mmpose.apis import init_model

        pose_model = init_model(
            models["poseConfig"],
            models["poseCheckpoint"],
            device=job.get("device", "cuda:0"),
        )
    except Exception as error:
        pose_error = str(error)
        try:
            pose_model = mediapipe_landmarkers(
                models["mediaPipePose"],
                models["mediaPipeHands"],
            )
            pose_error = f"DWPose unavailable ({error}); MediaPipe fallback active."
        except Exception as fallback_error:
            pose_error = f"DWPose unavailable ({error}); MediaPipe unavailable ({fallback_error})."

    clip_model = None
    clip_preprocess = None
    clip_text = None
    clip_device = "cpu"
    clip_error = ""
    try:
        clip_model, clip_preprocess, clip_text, clip_device = load_openclip(
            models["openClip"],
            job.get("device", "cuda:0"),
        )
    except Exception as error:
        clip_error = str(error)
    anchor_clip_scores = []
    if clip_model is not None:
        anchor_clip_scores = [
            openclip_score(
                clip_model,
                clip_preprocess,
                clip_text,
                clip_device,
                record["path"],
            )["commercialProbability"]
            for record in anchor_records
        ]
    commercial_threshold = (
        max(0.20, min(anchor_clip_scores) - 0.08) if anchor_clip_scores else 1.0
    )

    results = []
    for item in job["candidates"]:
        path = Path(item["path"])
        category = item["category"]
        image = cv2.imread(str(path))
        if image is None:
            results.append({"path": str(path), "overall": "REJECT", "reasons": ["invalid-image"]})
            continue
        height, width = image.shape[:2]
        faces = detect_faces(detector, image)
        significant_faces = primary_faces(faces)
        reasons = []
        checks: dict[str, Any] = {}
        resolution_ok = (
            width * height >= 1_000_000
            and min(width, height) >= 720
            and max(width, height) >= 1024
        )
        checks["resolution"] = {
            "ok": resolution_ok,
            "width": width,
            "height": height,
            "megapixels": round(width * height / 1_000_000, 4),
        }
        if not resolution_ok:
            reasons.append("low-resolution")
        if len(significant_faces) != 1:
            reasons.append("face-count")
            results.append(
                {
                    "path": str(path),
                    "category": category,
                    "overall": "REJECT",
                    "reasons": reasons,
                    "checks": checks
                    | {"faceCount": {"ok": False, "count": len(significant_faces), "rawCount": len(faces)}},
                    "score": 0.0,
                }
            )
            continue

        face = primary_face(significant_faces)
        feature = face_feature(recognizer, image, face)
        similarities = [
            float(recognizer.match(feature, record["feature"], cv2.FaceRecognizerSF_FR_COSINE))
            for record in anchor_records
        ]
        anchor_passes = sum(score >= identity_threshold for score in similarities)
        identity_ok = anchor_passes >= int(job.get("minimumAnchorPasses", 3))
        checks["identity"] = {
            "ok": identity_ok,
            "threshold": round(identity_threshold, 4),
            "anchorPasses": anchor_passes,
            "similarities": [round(score, 4) for score in similarities],
            "mean": round(float(np.mean(similarities)), 4),
        }
        if not identity_ok:
            reasons.append("identity-drift")

        candidate_geometry = geometry(face)
        geometry_error = float(np.mean(np.abs(candidate_geometry - reference_geometry)))
        geometry_score = max(0.0, 1.0 - geometry_error / 0.12)
        geometry_ok = geometry_score >= geometry_threshold
        checks["facialGeometry"] = {
            "ok": geometry_ok,
            "score": round(geometry_score, 4),
            "threshold": round(geometry_threshold, 4),
        }
        if not geometry_ok:
            reasons.append("facial-geometry-drift")

        candidate_hair = hair_hsv(image, face)
        hair_score = hsv_similarity(candidate_hair, reference_hair)
        hair_ok = hair_score >= 0.58
        checks["hair"] = {"ok": hair_ok, "score": round(hair_score, 4)}
        if not hair_ok:
            reasons.append("hair-color-drift")

        texture = skin_texture(image, face)
        texture_floor = max(12.0, reference_texture * 0.28)
        texture_ok = texture >= texture_floor
        checks["skinTexture"] = {
            "ok": texture_ok,
            "laplacianVariance": round(texture, 3),
            "minimum": round(texture_floor, 3),
        }
        if not texture_ok:
            reasons.append("over-smoothed-skin")

        face_height_ratio = float(face[3] / height)
        ratio_ranges = {
            "close_up": (0.24, 0.72),
            "upper_body": (0.14, 0.45),
            "full_body": (0.055, 0.25),
            "left_right_profile": (0.19, 0.62),
            "expressions": (0.22, 0.70),
            "poses": (0.07, 0.35),
        }
        lower, upper = ratio_ranges[category]
        proportion_ok = lower <= face_height_ratio <= upper
        checks["bodyProportion"] = {
            "ok": proportion_ok,
            "faceHeightRatio": round(face_height_ratio, 4),
            "expectedRange": [lower, upper],
        }
        if not proportion_ok:
            reasons.append("body-proportion-drift")

        contamination = edge_contamination(image)
        checks["contamination"] = contamination
        if not contamination["ok"]:
            reasons.append("text-watermark-or-collage")

        semantic = (
            openclip_score(
                clip_model,
                clip_preprocess,
                clip_text,
                clip_device,
                str(path),
            )
            if clip_model is not None
            else {
                "commercialProbability": 0.0,
                "contaminationProbability": 1.0,
                "artifactProbability": 1.0,
            }
        )
        semantic_ok = (
            clip_model is not None
            and semantic["commercialProbability"] >= commercial_threshold
            and semantic["contaminationProbability"] < 0.55
            and semantic["artifactProbability"] < 0.55
        )
        checks["openClipCommercial"] = {
            "ok": semantic_ok,
            "threshold": round(commercial_threshold, 4),
            **semantic,
        }
        if not semantic_ok:
            reasons.append("openclip-commercial-quality")

        anatomy = pose_result(pose_model, image, category)
        checks["anatomy"] = anatomy
        anatomy_required = category in {"upper_body", "full_body", "poses"}
        if anatomy_required and not anatomy["ok"]:
            reasons.append("hand-or-limb-defect")

        components = [
            min(1.0, max(0.0, (float(np.mean(similarities)) + 0.1) / 0.75)),
            geometry_score,
            hair_score,
            min(1.0, texture / max(reference_texture, 1.0)),
            1.0 if proportion_ok else 0.35,
            anatomy["score"] if anatomy_required else 1.0,
            1.0 if contamination["ok"] else 0.3,
            semantic["commercialProbability"],
            1.0 if resolution_ok else 0.3,
        ]
        score = round(sum(components) / len(components), 4)
        results.append(
            {
                "path": str(path),
                "category": category,
                "overall": "PASS" if not reasons else "REJECT",
                "reasons": reasons,
                "checks": checks,
                "score": score,
            }
        )

    report = {
        "schema": "temple-ai-studio.emma-synthetic-quality.v1",
        "identityThreshold": round(identity_threshold, 4),
        "facialGeometryThreshold": round(geometry_threshold, 4),
        "minimumAnchorPasses": int(job.get("minimumAnchorPasses", 3)),
        "anchorCalibration": {
            "minimumInterAnchorSimilarity": round(min(inter_anchor), 4) if inter_anchor else None,
            "medianInterAnchorSimilarity": round(median(inter_anchor), 4) if inter_anchor else None,
        },
        "poseModel": {
            "loaded": pose_model is not None,
            "error": pose_error,
        },
        "openClipModel": {
            "loaded": clip_model is not None,
            "error": clip_error,
            "device": str(clip_device),
            "commercialThreshold": round(commercial_threshold, 4),
        },
        "results": results,
        "summary": {
            "total": len(results),
            "approved": sum(item["overall"] == "PASS" for item in results),
            "rejected": sum(item["overall"] != "PASS" for item in results),
        },
    }
    atomic_json(Path(args.output), report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
