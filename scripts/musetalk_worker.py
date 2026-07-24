from __future__ import annotations

import argparse
import os
import runpy
import shutil
import sys
import types
import uuid
from pathlib import Path

import cv2
import numpy as np
import yaml


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


def install_preprocessing_compatibility(root: Path) -> None:
    """Use YuNet face geometry when MMEngine's compiled Windows ops are unavailable."""
    module = types.ModuleType("musetalk.utils.preprocessing")
    module.coord_placeholder = (0.0, 0.0, 0.0, 0.0)
    yunet = (
        root.parent.parent
        / "models"
        / "opencv"
        / "face_detection_yunet_2023mar.onnx"
    )
    if not yunet.is_file():
        raise FileNotFoundError(f"YuNet model not found: {yunet}")
    detector = cv2.FaceDetectorYN.create(str(yunet), "", (320, 320), 0.55, 0.3, 5000)

    def read_imgs(img_list):
        return [cv2.imread(str(path)) for path in img_list]

    def get_landmark_and_bbox(img_list, upperbondrange=0):
        frames = read_imgs(img_list)
        coordinates = []
        for frame in frames:
            if frame is None:
                coordinates.append(module.coord_placeholder)
                continue
            height, width = frame.shape[:2]
            detector.setInputSize((width, height))
            faces = detector.detect(frame)[1]
            if faces is None or not len(faces):
                coordinates.append(module.coord_placeholder)
                continue
            face = faces[int(np.argmax(faces[:, 2] * faces[:, 3]))]
            x, y, face_width, face_height = face[:4]
            margin_x = face_width * 0.08
            x1 = max(0, int(x - margin_x))
            x2 = min(width, int(x + face_width + margin_x))
            y1 = max(0, int(y + upperbondrange))
            y2 = min(height, int(y + face_height * 1.12))
            coordinates.append((x1, y1, x2, y2))
        return coordinates, frames

    module.read_imgs = read_imgs
    module.get_landmark_and_bbox = get_landmark_and_bbox
    sys.modules["musetalk.utils.preprocessing"] = module


def prepare_space_safe_job(config: Path, base_root: Path) -> tuple[Path, Path]:
    job_root = (
        base_root
        / "jobs"
        / f"musetalk-{uuid.uuid4().hex[:12]}"
    )
    inputs = job_root / "inputs"
    results = job_root / "results"
    inputs.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_load(config.read_text(encoding="utf-8-sig"))
    copy_index = 0

    def sanitize(value):
        nonlocal copy_index
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if not isinstance(value, str):
            return value
        source = Path(value)
        if not source.is_file():
            return value
        copy_index += 1
        target = inputs / f"asset_{copy_index:03d}{source.suffix.lower()}"
        shutil.copy2(source, target)
        return target.as_posix()

    sanitized = sanitize(payload)
    sanitized_path = job_root / "inference.yaml"
    sanitized_path.write_text(
        yaml.safe_dump(sanitized, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return sanitized_path, results


def main() -> int:
    parser = argparse.ArgumentParser(description="Temple AI Studio MuseTalk 1.5 worker.")
    parser.add_argument("--musetalk-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--ffmpeg-dir", required=True)
    parser.add_argument("--gpu", default="0")
    args = parser.parse_args()

    root = Path(args.musetalk_root).resolve()
    config = Path(args.config).resolve()
    output = Path(args.output_dir).resolve()
    output_file = Path(args.output_file).resolve()
    if not (root / "scripts" / "inference.py").is_file():
        raise FileNotFoundError(f"MuseTalk source not found: {root}")
    if not config.is_file():
        raise FileNotFoundError(str(config))
    output.mkdir(parents=True, exist_ok=True)
    safe_config, safe_output = prepare_space_safe_job(
        config,
        root.parent.parent.parent / "TempleAIStudioRuntime",
    )
    install_numba_compatibility_shim()
    install_preprocessing_compatibility(root)
    import torch

    original_torch_load = torch.load

    def trusted_local_weight_load(*load_args, **load_kwargs):
        load_kwargs.setdefault("weights_only", False)
        return original_torch_load(*load_args, **load_kwargs)

    torch.load = trusted_local_weight_load
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ["PYTHONPATH"] = str(root)
    cache_root = root.parent.parent / "cache"
    os.environ["HF_HOME"] = str(cache_root / "huggingface")
    os.environ["TRANSFORMERS_CACHE"] = str(cache_root / "transformers")
    os.environ["MPLCONFIGDIR"] = str(cache_root / "matplotlib")
    os.chdir(root)
    sys.path.insert(0, str(root))
    sys.argv = [
        str(root / "scripts" / "inference.py"),
        "--inference_config",
        str(safe_config),
        "--result_dir",
        str(safe_output),
        "--unet_model_path",
        str(root / "models" / "musetalkV15" / "unet.pth"),
        "--unet_config",
        str(root / "models" / "musetalkV15" / "musetalk.json"),
        "--version",
        "v15",
        "--ffmpeg_path",
        str(Path(args.ffmpeg_dir).resolve()),
        "--output_vid_name",
        str(safe_output / "final.mp4"),
        "--use_float16",
    ]
    runpy.run_path(str(root / "scripts" / "inference.py"), run_name="__main__")
    generated = sorted(
        safe_output.rglob("*.mp4"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not generated:
        raise RuntimeError(f"MuseTalk completed without an MP4 in {safe_output}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if generated[0].resolve() != output_file:
        shutil.copy2(generated[0], output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
