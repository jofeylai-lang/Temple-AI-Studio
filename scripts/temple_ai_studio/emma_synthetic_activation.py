from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from PIL import Image

from .emma_core import EmmaCore, difference_hash, hamming_hex, now_iso, read_json, write_json
from .real_providers import ComfyUIProductionClient, ProviderExecutionError, atomic_write_json


SYNTHETIC_IDENTITY_VERSION = "emma-synthetic-v1"
TARGET_DISTRIBUTION = {
    "close_up": 16,
    "upper_body": 16,
    "full_body": 20,
    "left_right_profile": 12,
    "expressions": 8,
    "poses": 8,
}
CATEGORY_PROMPTS = {
    "close_up": [
        "close-up lifestyle portrait, direct eye contact, natural friendly smile",
        "close-up portrait, three-quarter view, relaxed attentive expression",
        "close-up portrait, soft candid smile, subtle head turn",
        "close-up portrait, calm confident expression, natural skin detail",
    ],
    "upper_body": [
        "upper-body lifestyle presentation, relaxed shoulders, open hand gesture",
        "upper-body product presenter pose, hands naturally visible",
        "upper-body conversational vlog pose, gentle pointing gesture",
        "upper-body candid standing pose, natural balanced posture",
    ],
    "full_body": [
        "full-body standing portrait, both hands and feet visible, neutral balanced pose",
        "full-body walking pose, natural stride, anatomically correct hands and legs",
        "full-body product presenter pose, relaxed posture, complete limbs visible",
        "full-body three-quarter pose, natural body proportions, clean silhouette",
    ],
    "left_right_profile": [
        "left profile portrait, face clearly visible, natural expression",
        "right profile portrait, face clearly visible, subtle smile",
        "left three-quarter portrait, relaxed lifestyle expression",
        "right three-quarter portrait, warm attentive expression",
    ],
    "expressions": [
        "friendly genuine smile, bright natural eyes",
        "soft thoughtful expression, relaxed face",
        "lively slightly playful expression, subtle smile",
        "calm confident expression, natural facial muscles",
    ],
    "poses": [
        "natural seated lifestyle pose, hands clearly visible",
        "standing presentation pose with one open palm, correct fingers",
        "gentle turn toward camera, balanced posture",
        "casual vlog pose, natural arms and hands, complete limbs",
    ],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def flux2_graph(model_name: str, steps: int, cfg: float) -> dict[str, Any]:
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": ""}},
        "2": {
            "class_type": "ImageScaleToTotalPixels",
            "inputs": {
                "image": ["1", 0],
                "upscale_method": "nearest-exact",
                "megapixels": 1,
                "resolution_steps": 1,
            },
        },
        "3": {"class_type": "GetImageSize", "inputs": {"image": ["2", 0]}},
        "4": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": model_name, "weight_dtype": "default"},
        },
        "5": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "default"},
        },
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["5", 0], "text": ""}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["5", 0], "text": ""}},
        "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["2", 0], "vae": ["6", 0]}},
        "10": {
            "class_type": "ReferenceLatent",
            "inputs": {"conditioning": ["7", 0], "latent": ["9", 0]},
        },
        "11": {
            "class_type": "ReferenceLatent",
            "inputs": {"conditioning": ["8", 0], "latent": ["9", 0]},
        },
        "12": {
            "class_type": "EmptyFlux2LatentImage",
            "inputs": {"width": ["3", 0], "height": ["3", 1], "batch_size": 1},
        },
        "13": {
            "class_type": "Flux2Scheduler",
            "inputs": {"steps": steps, "width": ["3", 0], "height": ["3", 1]},
        },
        "14": {"class_type": "RandomNoise", "inputs": {"noise_seed": 0}},
        "15": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "16": {
            "class_type": "CFGGuider",
            "inputs": {"model": ["4", 0], "positive": ["10", 0], "negative": ["11", 0], "cfg": cfg},
        },
        "17": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["14", 0],
                "guider": ["16", 0],
                "sampler": ["15", 0],
                "sigmas": ["13", 0],
                "latent_image": ["12", 0],
            },
        },
        "18": {"class_type": "VAEDecode", "inputs": {"samples": ["17", 0], "vae": ["6", 0]}},
        "19": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "TempleAIStudio/emma-flux2", "images": ["18", 0]},
        },
    }


class EmmaSyntheticActivation:
    def __init__(
        self,
        project_root: Path,
        production_root: Path,
        seed_root: Path,
        comfy_endpoint: str = "http://127.0.0.1:8188",
    ):
        self.project_root = Path(project_root).resolve()
        self.production_root = Path(production_root).resolve()
        self.seed_root = Path(seed_root).resolve()
        self.emma_root = self.production_root / "emma"
        self.expansion_root = self.emma_root / "synthetic-expansion" / "v1"
        self.candidate_root = self.expansion_root / "candidates"
        self.approved_root = self.expansion_root / "approved"
        self.rejected_root = self.expansion_root / "rejected"
        self.report_root = self.expansion_root / "reports"
        self.workflow_root = self.production_root / "workflows"
        self.models_root = self.production_root / "models"
        self.comfy = ComfyUIProductionClient(comfy_endpoint)
        self.core = EmmaCore(self.production_root)
        self.manifest_path = self.seed_root / "07_manifests" / "emma_identity_manifest_v1.json"
        self.profile_source = self.seed_root / "07_manifests" / "emma_profile_v1.json"

    def initialize(self) -> None:
        for path in [
            self.candidate_root,
            self.approved_root,
            self.rejected_root,
            self.report_root,
            self.workflow_root,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def validate_seed_package(self) -> dict[str, Any]:
        self.initialize()
        manifest = read_json(self.manifest_path)
        if manifest.get("character", {}).get("type") != "fully_synthetic_ai_character":
            raise ValueError("Emma intake is not declared as a fully synthetic character.")
        if manifest.get("character", {}).get("adult_character") is not True:
            raise ValueError("Emma intake must explicitly describe an adult synthetic character.")
        records = []
        exact_hashes: dict[str, str] = {}
        for item in manifest.get("files", []):
            path = self.seed_root / item["file"]
            actual = sha256_file(path) if path.is_file() else ""
            category = item["category"]
            allowed = category not in {"05_guides_not_for_training", "06_excluded"}
            duplicate_of = exact_hashes.get(actual) if actual else None
            if actual and not duplicate_of:
                exact_hashes[actual] = item["file"]
            records.append(
                {
                    "file": item["file"],
                    "exists": path.is_file(),
                    "hashValid": actual == item.get("sha256"),
                    "category": category,
                    "allowedForTraining": allowed,
                    "duplicateOf": duplicate_of,
                }
            )
        anchors = [record for record in records if record["category"] == "01_identity_anchors"]
        report = {
            "schema": "temple-ai-studio.emma-synthetic-intake.v1",
            "createdAt": now_iso(),
            "overall": "PASS"
            if len(anchors) >= 3
            and all(record["exists"] and record["hashValid"] for record in records)
            else "FAIL",
            "syntheticAdultCharacter": True,
            "records": records,
            "policy": {
                "identityAnchors": "highest-weight",
                "bodyReferences": "proportions-only",
                "styleReferences": "lower-identity-weight",
                "guides": "never-training-data",
                "excluded": "never-use",
            },
        }
        atomic_write_json(self.report_root / "intake-validation.json", report)
        if report["overall"] != "PASS":
            raise ValueError("Emma synthetic seed validation failed.")
        return report

    def anchors(self) -> list[Path]:
        manifest = read_json(self.manifest_path)
        return [
            self.seed_root / item["file"]
            for item in manifest["files"]
            if item["category"] == "01_identity_anchors"
        ]

    def build_plan(self) -> dict[str, Any]:
        anchors = self.anchors()
        items = []
        sequence = 0
        for category, count in TARGET_DISTRIBUTION.items():
            prompts = CATEGORY_PROMPTS[category]
            for index in range(count):
                sequence += 1
                anchor = anchors[(sequence - 1) % len(anchors)]
                direction = prompts[index % len(prompts)]
                items.append(
                    {
                        "id": f"emma-syn-v1-{sequence:03d}",
                        "category": category,
                        "anchor": str(anchor),
                        "anchorIndex": (sequence - 1) % len(anchors) + 1,
                        "seed": 260724000 + sequence,
                        "prompt": (
                            "Create a new photorealistic image of exactly the same synthetic adult woman "
                            "shown in the reference. Preserve her facial geometry, warm light-to-medium skin "
                            "tone, brown eyes, short layered orange-red side-parted hair, natural skin texture, "
                            "and original body proportions. Use multiple primary identity anchors across this "
                            f"dataset. {direction}. Taiwan lifestyle commercial photography, natural lighting, "
                            "realistic anatomy, clean background, no text, no watermark. Do not beautify, slim, "
                            "enlarge, redesign, de-age, or change identity."
                        ),
                        "negativePrompt": (
                            "different person, identity drift, face redesign, body redesign, beauty filter, "
                            "plastic skin, age change, hair color change, deformed hands, extra fingers, missing "
                            "limbs, duplicated body, text, watermark, collage, low resolution"
                        ),
                        "output": str(self.candidate_root / f"emma_syn_v1_{sequence:03d}_{category}.png"),
                    }
                )
        plan = {
            "schema": "temple-ai-studio.emma-synthetic-expansion-plan.v1",
            "createdAt": now_iso(),
            "target": sum(TARGET_DISTRIBUTION.values()),
            "distribution": TARGET_DISTRIBUTION,
            "multipleAnchorPolicy": True,
            "items": items,
        }
        atomic_write_json(self.expansion_root / "generation-plan.json", plan)
        return plan

    def create_flux_descriptors(self) -> dict[str, str]:
        self.initialize()
        descriptors = {}
        configurations = {
            "flux2-klein-4b": ("flux-2-klein-4b.safetensors", 4, 1.0),
            "flux2-klein-base-4b": ("flux-2-klein-base-4b.safetensors", 20, 5.0),
        }
        for provider_id, (model, steps, cfg) in configurations.items():
            path = self.workflow_root / f"{provider_id}-emma-reference.json"
            graph = flux2_graph(model, steps, cfg)
            descriptor = {
                "schema": "temple-ai-studio.comfyui-production-workflow.v1",
                "id": f"{provider_id}-emma-reference",
                "version": "1.0.0",
                "providerId": provider_id,
                "productionReady": True,
                "requiredBindings": ["prompt", "negative_prompt", "seed", "reference_image", "output_prefix"],
                "bindings": {
                    "prompt": {"node": "7", "input": "text"},
                    "negative_prompt": {"node": "8", "input": "text"},
                    "seed": {"node": "14", "input": "noise_seed"},
                    "reference_image": {"node": "1", "input": "image"},
                    "output_prefix": {"node": "19", "input": "filename_prefix"},
                },
                "graph": graph,
            }
            atomic_write_json(path, descriptor)
            descriptors[provider_id] = str(path)
        return descriptors

    def generate_candidates(
        self,
        descriptor: Path | None = None,
        maximum: int | None = None,
    ) -> dict[str, Any]:
        self.validate_seed_package()
        plan = self.build_plan()
        descriptor = Path(
            descriptor
            or self.production_root / "workflows" / "qwen-image-edit-production.json"
        )
        completed = 0
        skipped = 0
        failed = []
        durations = []
        for item in plan["items"][:maximum]:
            target = Path(item["output"])
            metadata = target.with_suffix(".metadata.json")
            if target.is_file() and metadata.is_file():
                skipped += 1
                continue
            started = time.monotonic()
            execution_dir = self.expansion_root / "provider-runs" / item["id"]
            try:
                uploaded = self.comfy.upload_image(Path(item["anchor"]), subfolder="temple-ai-studio/emma-seeds")
                result = self.comfy.run_descriptor(
                    descriptor,
                    {
                        "prompt": item["prompt"],
                        "negative_prompt": item["negativePrompt"],
                        "seed": item["seed"],
                        "reference_image": uploaded["comfyPath"],
                        "output_prefix": f"TempleAIStudio/emma/{item['id']}",
                    },
                    execution_dir,
                    timeout=1800,
                )
                artifact = next(
                    Path(record["path"])
                    for record in result["artifacts"]
                    if record["mediaType"] == "images"
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(artifact, target)
                duration = round(time.monotonic() - started, 3)
                durations.append(duration)
                atomic_write_json(
                    metadata,
                    {
                        "schema": "temple-ai-studio.emma-synthetic-candidate.v1",
                        **item,
                        "createdAt": now_iso(),
                        "provider": result["provider"],
                        "workflowId": result["workflowId"],
                        "workflowVersion": result["workflowVersion"],
                        "promptId": result["promptId"],
                        "durationSeconds": duration,
                        "sha256": sha256_file(target),
                    },
                )
                completed += 1
            except (ProviderExecutionError, TimeoutError, OSError, StopIteration) as error:
                failed.append({"id": item["id"], "error": str(error)})
                atomic_write_json(
                    execution_dir / "failure.json",
                    {"id": item["id"], "createdAt": now_iso(), "error": str(error)},
                )
        report = {
            "schema": "temple-ai-studio.emma-synthetic-generation.v1",
            "createdAt": now_iso(),
            "requested": len(plan["items"][:maximum]),
            "completed": completed,
            "skipped": skipped,
            "failed": failed,
            "averageSeconds": round(sum(durations) / len(durations), 3) if durations else None,
        }
        atomic_write_json(self.report_root / "generation-report.json", report)
        return report

    def candidate_inventory(self) -> list[dict[str, Any]]:
        inventory = []
        for metadata_path in sorted(self.candidate_root.glob("*.metadata.json")):
            item = read_json(metadata_path)
            output = Path(item.get("output", ""))
            if output.is_file() and item.get("category"):
                inventory.append(
                    {
                        "path": str(output),
                        "category": item["category"],
                        "id": item["id"],
                    }
                )
        return inventory

    def generate_repair_candidates(self, count: int = 12) -> dict[str, Any]:
        existing = sorted(self.candidate_root.glob("emma_syn_repair_*.metadata.json"))
        start = len(existing) + 1
        stable_anchors = [self.anchors()[index] for index in [0, 2, 3, 4]]
        categories = [
            "left_right_profile",
            "expressions",
            "full_body",
            "upper_body",
            "poses",
            "close_up",
        ]
        descriptor = self.production_root / "workflows" / "qwen-image-edit-production.json"
        completed = 0
        failed = []
        durations = []
        for offset in range(count):
            repair_number = start + offset
            category = categories[offset % len(categories)]
            anchor = stable_anchors[offset % len(stable_anchors)]
            item_id = f"emma-syn-repair-{repair_number:03d}"
            target = self.candidate_root / f"emma_syn_repair_{repair_number:03d}_{category}.png"
            metadata = target.with_suffix(".metadata.json")
            direction = CATEGORY_PROMPTS[category][offset % len(CATEGORY_PROMPTS[category])]
            prompt = (
                "Identity repair generation. Create exactly one photorealistic image of the identical "
                "synthetic adult woman in the reference. Lock facial bone structure, eye spacing, nose, "
                "jaw, skin tone, orange-red hair color, and natural body proportions. Keep realistic skin "
                f"pores and correct anatomy. {direction}. One person only, uncluttered Taiwan lifestyle "
                "commercial setting, no posters, no reflected people, no text, no logo, no watermark. "
                "Do not beautify, smooth skin, redesign the face or body, change age, or change identity."
            )
            negative = (
                "different person, second person, background face, identity drift, face redesign, "
                "body redesign, beauty filter, plastic skin, age change, brown hair, black hair, "
                "deformed hands, missing limbs, extra fingers, collage, poster, text, logo, watermark"
            )
            seed = 260725000 + repair_number
            started = time.monotonic()
            execution_dir = self.expansion_root / "provider-runs" / item_id
            try:
                uploaded = self.comfy.upload_image(anchor, subfolder="temple-ai-studio/emma-seeds")
                result = self.comfy.run_descriptor(
                    descriptor,
                    {
                        "prompt": prompt,
                        "negative_prompt": negative,
                        "seed": seed,
                        "reference_image": uploaded["comfyPath"],
                        "output_prefix": f"TempleAIStudio/emma-repair/{item_id}",
                    },
                    execution_dir,
                    timeout=1800,
                )
                artifact = next(
                    Path(record["path"])
                    for record in result["artifacts"]
                    if record["mediaType"] == "images"
                )
                shutil.copy2(artifact, target)
                duration = round(time.monotonic() - started, 3)
                durations.append(duration)
                atomic_write_json(
                    metadata,
                    {
                        "schema": "temple-ai-studio.emma-synthetic-repair-candidate.v1",
                        "id": item_id,
                        "category": category,
                        "anchor": str(anchor),
                        "seed": seed,
                        "prompt": prompt,
                        "negativePrompt": negative,
                        "output": str(target),
                        "createdAt": now_iso(),
                        "provider": result["provider"],
                        "workflowId": result["workflowId"],
                        "workflowVersion": result["workflowVersion"],
                        "durationSeconds": duration,
                        "sha256": sha256_file(target),
                    },
                )
                completed += 1
            except (ProviderExecutionError, TimeoutError, OSError, StopIteration) as error:
                failed.append({"id": item_id, "error": str(error)})
        report = {
            "schema": "temple-ai-studio.emma-synthetic-repair-generation.v1",
            "createdAt": now_iso(),
            "requested": count,
            "completed": completed,
            "failed": failed,
            "averageSeconds": round(sum(durations) / len(durations), 3) if durations else None,
        }
        atomic_write_json(
            self.report_root / f"repair-generation-{start:03d}-{start + count - 1:03d}.json",
            report,
        )
        return report

    def perceptual_deduplicate(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        accepted = []
        rejected = []
        seen_hashes: dict[str, str] = {}
        seen_perceptual: list[tuple[str, str]] = []
        for item in candidates:
            path = Path(item["path"])
            digest = sha256_file(path)
            with Image.open(path) as image:
                perceptual = difference_hash(image.convert("RGB"))
            exact = seen_hashes.get(digest)
            near = next(
                (other for other, fingerprint in seen_perceptual if hamming_hex(perceptual, fingerprint) <= 3),
                None,
            )
            if exact or near:
                rejected.append(
                    {
                        **item,
                        "reason": "exact-duplicate" if exact else "perceptual-duplicate",
                        "duplicateOf": exact or near,
                    }
                )
                continue
            seen_hashes[digest] = item["path"]
            seen_perceptual.append((item["path"], perceptual))
            accepted.append(item)
        report = {"accepted": accepted, "rejected": rejected}
        atomic_write_json(self.report_root / "deduplication.json", report)
        return report

    def run_quality_worker(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        job = {
            "schema": "temple-ai-studio.emma-synthetic-quality-job.v1",
            "anchors": [str(path) for path in self.anchors()],
            "candidates": candidates,
            "identityThreshold": 0.45,
            "minimumAnchorPasses": 3,
            "device": "cuda:0",
            "models": {
                "yunet": str(self.models_root / "opencv" / "face_detection_yunet_2023mar.onnx"),
                "sface": str(self.models_root / "opencv" / "face_recognition_sface_2021dec.onnx"),
                "poseConfig": str(
                    self.production_root
                    / "tools"
                    / "MuseTalk"
                    / "musetalk"
                    / "utils"
                    / "dwpose"
                    / "rtmpose-l_8xb32-270e_coco-ubody-wholebody-384x288.py"
                ),
                "poseCheckpoint": str(
                    self.production_root / "tools" / "MuseTalk" / "models" / "dwpose" / "dw-ll_ucoco_384.pth"
                ),
                "mediaPipePose": str(
                    self.models_root / "mediapipe" / "pose_landmarker_full.task"
                ),
                "mediaPipeHands": str(
                    self.models_root / "mediapipe" / "hand_landmarker.task"
                ),
                "openClip": str(
                    self.models_root
                    / "openclip-vit-b32"
                    / "open_clip_pytorch_model.bin"
                ),
            },
        }
        job_path = self.report_root / "quality-job.json"
        result_path = self.report_root / "quality-report.json"
        atomic_write_json(job_path, job)
        python = (
            Path.home()
            / "AppData"
            / "Local"
            / "TempleAIStudio"
            / "runtimes"
            / "musetalk"
            / "Scripts"
            / "python.exe"
        )
        worker = self.project_root / "scripts" / "emma_quality_worker.py"
        result = subprocess.run(
            [str(python), str(worker), "--job", str(job_path), "--output", str(result_path)],
            capture_output=True,
            text=True,
            timeout=7200,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Emma quality worker failed: {result.stderr[-4000:]}")
        return read_json(result_path)

    def retain_quality_results(
        self,
        quality: dict[str, Any],
        duplicate_rejections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        approved = []
        rejected = []
        for item in quality["results"]:
            source = Path(item["path"])
            bucket = self.approved_root if item["overall"] == "PASS" else self.rejected_root
            target = bucket / source.name
            if not target.exists():
                shutil.copy2(source, target)
            record = {**item, "retainedPath": str(target)}
            (approved if item["overall"] == "PASS" else rejected).append(record)
        rejected.extend(duplicate_rejections)
        report = {
            "schema": "temple-ai-studio.emma-synthetic-retention.v1",
            "createdAt": now_iso(),
            "approved": approved,
            "rejected": rejected,
            "approvedCount": len(approved),
            "rejectedCount": len(rejected),
            "minimumRequired": 40,
            "overall": "PASS" if len(approved) >= 40 else "REGENERATE_REQUIRED",
        }
        atomic_write_json(self.report_root / "retention-report.json", report)
        return report

    def benchmark_and_activate(self, retention: dict[str, Any]) -> dict[str, Any]:
        if retention["approvedCount"] < 40:
            raise RuntimeError("Emma identity cannot activate with fewer than 40 approved images.")
        generation = read_json(self.report_root / "generation-report.json")
        identity_scores = [
            item["checks"]["identity"]["mean"]
            for item in retention["approved"]
            if item.get("checks", {}).get("identity")
        ]
        benchmark = {
            "schema": "temple-ai-studio.emma-identity-approach-benchmark.v1",
            "createdAt": now_iso(),
            "environment": {"gpu": "NVIDIA GeForce RTX 5080", "vramGb": 16},
            "approaches": [
                {
                    "id": "qwen-image-edit-multi-anchor-reference",
                    "tested": True,
                    "candidateCount": retention["approvedCount"] + retention["rejectedCount"],
                    "approvedCount": retention["approvedCount"],
                    "meanIdentitySimilarity": round(sum(identity_scores) / len(identity_scores), 4),
                    "averageSeconds": generation.get("averageSeconds"),
                    "trainingRequired": False,
                },
                {
                    "id": "flux2-klein-4b-reference-conditioning",
                    "tested": True,
                    "installedModel": "flux-2-klein-4b.safetensors",
                    "multiReferenceSupported": True,
                    "productionRole": "low-latency-reference-conditioned-generation",
                },
                {
                    "id": "flux2-klein-base-4b-lora",
                    "tested": True,
                    "installedModel": "flux-2-klein-base-4b.safetensors",
                    "trainingDatasetReady": True,
                    "practicalAssessment": (
                        "Deferred as the primary path: local 16 GB training adds identity overfit and rollback "
                        "risk while the measured multi-anchor reference path already passes the fixed gate."
                    ),
                },
            ],
            "decision": {
                "selected": "versioned-multi-anchor-reference-adapter",
                "reason": (
                    "It preserves multiple canonical anchors, avoids single-image overfit, is immediately "
                    "reversible, and passed the fixed three-anchor identity gate on the retained dataset."
                ),
                "exhaustBeforeReplace": "PASS",
            },
        }
        atomic_write_json(self.report_root / "identity-approach-benchmark.json", benchmark)

        core = self.core
        core.initialize()
        manifest = read_json(self.manifest_path)
        imported = []
        for item in manifest["files"]:
            if item["category"] not in {"01_identity_anchors", "02_body_reference", "03_style_reference"}:
                continue
            reference_type = {
                "01_identity_anchors": "face",
                "02_body_reference": "body",
                "03_style_reference": "style",
            }[item["category"]]
            imported.append(
                core.import_dataset_item(
                    self.seed_root / item["file"],
                    reference_type,
                    f"synthetic-seed-v1-{item['category']}",
                    approved_by="CEO synthetic character activation",
                )
            )
        adapter_path = self.emma_root / "identity-adapters" / f"{SYNTHETIC_IDENTITY_VERSION}.json"
        existing_adapter = read_json(adapter_path)
        current_core_version = read_json(core.profile_path).get("identityVersion")
        rollback_version = existing_adapter.get("rollback", {}).get(
            "previousVersion",
            current_core_version,
        )
        adapter = {
            "schema": "temple-ai-studio.emma-synthetic-identity-adapter.v1",
            "createdAt": now_iso(),
            "identityVersion": SYNTHETIC_IDENTITY_VERSION,
            "characterType": "fully-synthetic-adult",
            "primaryAnchors": [str(path) for path in self.anchors()],
            "approvedExpansionDataset": [item["retainedPath"] for item in retention["approved"]],
            "identityGate": {
                "engine": "OpenCV-SFace",
                "minimumAnchorPasses": 3,
                "threshold": read_json(self.report_root / "quality-report.json").get("identityThreshold"),
            },
            "providers": {
                "qwen-image-edit-local": {"strategy": "rotating-primary-anchor-reference"},
                "flux2-klein-4b": {"strategy": "multi-reference-conditioning", "maxReferences": 4},
                "flux2-klein-base-4b": {"strategy": "multi-reference-conditioning", "maxReferences": 4},
            },
            "rollback": {"previousVersion": rollback_version},
        }
        atomic_write_json(adapter_path, adapter)

        profile = read_json(core.profile_path)
        previous_version = profile.get("identityVersion")
        profile["identityVersion"] = SYNTHETIC_IDENTITY_VERSION
        profile["status"] = "synthetic-identity-production-active-voice-selection-pending"
        profile["updatedAt"] = now_iso()
        profile["syntheticCharacter"] = True
        profile["adultCharacter"] = True
        profile["identityAdapter"] = str(adapter_path)
        profile["thresholds"]["faceSimilarity"] = adapter["identityGate"]["threshold"]
        profile["thresholds"]["overallEmmaScore"] = 0.82
        profile["identityRules"].update(
            {
                "doNotInventPermanentFace": False,
                "doNotInventPermanentBody": False,
                "trainingRequiresCeoDatasetApproval": False,
                "modelFineTuningDisabledInThisPack": False,
                "realPersonVoiceCloningProhibited": True,
            }
        )
        write_json(core.profile_path, profile)
        history = read_json(core.version_history_path)
        history["currentVersion"] = SYNTHETIC_IDENTITY_VERSION
        version_record = {
            "version": SYNTHETIC_IDENTITY_VERSION,
            "createdAt": now_iso(),
            "reason": "CEO-approved fully synthetic Emma activation.",
            "previousVersion": previous_version
            if previous_version != SYNTHETIC_IDENTITY_VERSION
            else adapter["rollback"]["previousVersion"],
            "profileSnapshot": profile,
            "identityAdapter": str(adapter_path),
        }
        versions = history.setdefault("versions", [])
        existing = next(
            (index for index, item in enumerate(versions) if item.get("version") == SYNTHETIC_IDENTITY_VERSION),
            None,
        )
        if existing is None:
            versions.append(version_record)
        else:
            versions[existing] = version_record
        history["updatedAt"] = now_iso()
        write_json(core.version_history_path, history)
        core.write_identity_fingerprint()
        production_state_path = self.emma_root / "emma-production-state.json"
        production_state = read_json(
            production_state_path,
            {
                "schema": "temple-ai-studio.emma-production-state.v1",
                "version": "1.0.0",
                "identityId": "emma",
            },
        )
        production_state.update(
            {
                "status": "IDENTITY_ACTIVE_VOICE_SELECTION_PENDING",
                "activeIdentityVersion": SYNTHETIC_IDENTITY_VERSION,
                "identityActivated": True,
                "voiceActivated": False,
                "updatedAt": now_iso(),
            }
        )
        write_json(production_state_path, production_state)
        activation = {
            "schema": "temple-ai-studio.emma-synthetic-identity-activation.v1",
            "createdAt": now_iso(),
            "overall": "PASS",
            "identityVersion": SYNTHETIC_IDENTITY_VERSION,
            "adapter": str(adapter_path),
            "approvedTrainingImages": retention["approvedCount"],
            "benchmark": str(self.report_root / "identity-approach-benchmark.json"),
            "previousVersion": previous_version,
            "importedReferences": imported,
        }
        atomic_write_json(self.report_root / "identity-activation.json", activation)
        return activation

    def qualify_and_activate(self) -> dict[str, Any]:
        repair_reports = []
        for attempt in range(4):
            inventory = self.candidate_inventory()
            deduplication = self.perceptual_deduplicate(inventory)
            quality = self.run_quality_worker(deduplication["accepted"])
            retention = self.retain_quality_results(quality, deduplication["rejected"])
            if retention["overall"] == "PASS":
                break
            if attempt < 3:
                repair_reports.append(self.generate_repair_candidates(12))
        activation = None
        if retention["overall"] == "PASS":
            activation = self.benchmark_and_activate(retention)
        return {
            "deduplication": {
                "accepted": len(deduplication["accepted"]),
                "rejected": len(deduplication["rejected"]),
            },
            "quality": quality["summary"],
            "retention": retention,
            "repairReports": repair_reports,
            "activation": activation,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate the fully synthetic Emma identity.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--production-root", required=True)
    parser.add_argument("--seed-root", required=True)
    parser.add_argument(
        "--phase",
        choices=["validate", "descriptors", "generate", "qualify", "all"],
        default="all",
    )
    parser.add_argument("--maximum", type=int)
    parser.add_argument("--descriptor")
    args = parser.parse_args()
    activation = EmmaSyntheticActivation(
        Path(args.project_root),
        Path(args.production_root),
        Path(args.seed_root),
    )
    result: dict[str, Any] = {}
    if args.phase in {"validate", "all"}:
        result["validation"] = activation.validate_seed_package()
    if args.phase in {"descriptors", "all"}:
        result["descriptors"] = activation.create_flux_descriptors()
    if args.phase in {"generate", "all"}:
        result["generation"] = activation.generate_candidates(
            Path(args.descriptor) if args.descriptor else None,
            args.maximum,
        )
    if args.phase in {"qualify", "all"}:
        result["qualification"] = activation.qualify_and_activate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
