from __future__ import annotations

import hashlib
import json
import math
import shutil
import uuid
import wave
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from .emma_core import EmmaCore


EMMA_PRODUCTION_VERSION = "1.0.0"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VOICE_EXTENSIONS = {".wav"}
IDENTITY_KINDS = {"face", "half-body", "full-body", "profile", "expression", "pose"}
REQUIRED_CONSENT_USES = {"identity-training", "voice-cloning", "synthetic-media", "commercial-content"}
MINIMUM_IDENTITY_IMAGES = 20
RECOMMENDED_IDENTITY_IMAGES = 50
MINIMUM_VOICE_SECONDS = 600
RECOMMENDED_VOICE_SECONDS = 1800


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def average_hash(image: Image.Image, size: int = 8) -> str:
    gray = image.convert("L").resize((size, size))
    pixels = list(gray.get_flattened_data())
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if pixel >= average else "0" for pixel in pixels)
    return f"{int(bits, 2):016x}"


def difference_hash(image: Image.Image, size: int = 8) -> str:
    gray = image.convert("L").resize((size + 1, size))
    bits = []
    for y in range(size):
        for x in range(size):
            bits.append("1" if gray.getpixel((x, y)) > gray.getpixel((x + 1, y)) else "0")
    return f"{int(''.join(bits), 2):016x}"


def hamming_hex(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def analyze_identity_image(path: Path) -> dict[str, Any]:
    with Image.open(path) as source:
        source.verify()
    with Image.open(path) as source:
        image = source.convert("RGB")
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        mean_luma = float(stat.mean[0])
        contrast = float(stat.stddev[0])
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_score = float(ImageStat.Stat(edges).stddev[0])
        dynamic_range = float(max(gray.getextrema()) - min(gray.getextrema()))
        width, height = image.size
        checks = [
            {
                "name": "minimum-resolution",
                "ok": width >= 768 and height >= 768,
                "value": f"{width}x{height}",
                "requirement": "both dimensions >= 768",
            },
            {
                "name": "exposure",
                "ok": 35 <= mean_luma <= 225,
                "value": round(mean_luma, 2),
                "requirement": "35..225",
            },
            {
                "name": "contrast",
                "ok": contrast >= 18,
                "value": round(contrast, 2),
                "requirement": ">= 18",
            },
            {
                "name": "sharpness",
                "ok": edge_score >= 8,
                "value": round(edge_score, 2),
                "requirement": ">= 8",
            },
            {
                "name": "dynamic-range",
                "ok": dynamic_range >= 80,
                "value": round(dynamic_range, 2),
                "requirement": ">= 80",
            },
        ]
        return {
            "sha256": sha256_file(path),
            "perceptualHash": average_hash(image),
            "differenceHash": difference_hash(image),
            "width": width,
            "height": height,
            "meanLuma": round(mean_luma, 2),
            "contrast": round(contrast, 2),
            "edgeScore": round(edge_score, 2),
            "dynamicRange": round(dynamic_range, 2),
            "checks": checks,
            "overall": "PASS" if all(check["ok"] for check in checks) else "FAIL",
        }


def _pcm_values(raw: bytes, sample_width: int) -> list[int]:
    if sample_width == 1:
        return [value - 128 for value in raw]
    if sample_width == 2:
        values = array("h")
        values.frombytes(raw)
        return list(values)
    if sample_width == 3:
        values = []
        for index in range(0, len(raw) - 2, 3):
            value = int.from_bytes(raw[index : index + 3], "little", signed=False)
            if value & 0x800000:
                value -= 0x1000000
            values.append(value)
        return values
    if sample_width == 4:
        values = array("i")
        values.frombytes(raw)
        return list(values)
    raise ValueError(f"Unsupported PCM sample width: {sample_width}")


def analyze_voice_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        frame_count = source.getnframes()
        compression = source.getcomptype()
        raw = source.readframes(frame_count)
    values = _pcm_values(raw, sample_width)
    if channels > 1:
        values = values[::channels]
    max_amplitude = float((1 << (sample_width * 8 - 1)) - 1)
    normalized = [value / max_amplitude for value in values]
    rms = math.sqrt(sum(value * value for value in normalized) / max(1, len(normalized)))
    clipping_ratio = sum(1 for value in normalized if abs(value) >= 0.98) / max(1, len(normalized))
    silence_ratio = sum(1 for value in normalized if abs(value) <= 0.003) / max(1, len(normalized))
    zero_crossings = sum(
        1
        for left, right in zip(normalized, normalized[1:])
        if (left < 0 <= right) or (right < 0 <= left)
    )
    duration = frame_count / sample_rate if sample_rate else 0.0
    checks = [
        {"name": "pcm-wav", "ok": compression == "NONE", "value": compression},
        {"name": "mono", "ok": channels == 1, "value": channels},
        {"name": "sample-rate", "ok": 24000 <= sample_rate <= 48000, "value": sample_rate},
        {"name": "bit-depth", "ok": sample_width in {2, 3, 4}, "value": sample_width * 8},
        {"name": "clip-duration", "ok": 3 <= duration <= 30, "value": round(duration, 3)},
        {"name": "signal-level", "ok": 0.015 <= rms <= 0.35, "value": round(rms, 5)},
        {"name": "clipping", "ok": clipping_ratio <= 0.001, "value": round(clipping_ratio, 6)},
        {"name": "silence", "ok": silence_ratio <= 0.35, "value": round(silence_ratio, 4)},
    ]
    return {
        "sha256": sha256_file(path),
        "channels": channels,
        "sampleWidth": sample_width,
        "sampleRate": sample_rate,
        "durationSeconds": round(duration, 3),
        "rms": round(rms, 6),
        "clippingRatio": round(clipping_ratio, 6),
        "silenceRatio": round(silence_ratio, 4),
        "zeroCrossingRate": round(zero_crossings / max(1, len(normalized)), 6),
        "checks": checks,
        "overall": "PASS" if all(check["ok"] for check in checks) else "FAIL",
    }


class EmmaProductionActivator:
    def __init__(self, project_root: Path | str, data_root: Path | str):
        self.project_root = Path(project_root).resolve()
        self.root = Path(data_root).resolve()
        self.intake = self.root / "intake"
        self.identity_inbox = self.intake / "identity"
        self.voice_inbox = self.intake / "voice"
        self.consent_dir = self.intake / "consent"
        self.manifest_path = self.intake / "emma-intake.json"
        self.consent_path = self.consent_dir / "emma-consent.json"
        self.accepted = self.root / "datasets" / "accepted"
        self.rejected = self.root / "datasets" / "rejected"
        self.preparation = self.root / "preparation"
        self.versions = self.root / "versions"
        self.state_path = self.root / "emma-production-state.json"
        self.intake_report_path = self.root / "reports" / "intake-report.json"
        # Production identity data belongs beside other production data, not in
        # disposable or Git-tracked application files.
        self.core = EmmaCore(self.root.parent)

    def initialize(self) -> dict[str, Any]:
        for path in [
            self.identity_inbox,
            self.voice_inbox,
            self.consent_dir,
            self.accepted / "identity",
            self.accepted / "voice",
            self.rejected / "identity",
            self.rejected / "voice",
            self.preparation,
            self.versions,
            self.root / "reports",
        ]:
            path.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            atomic_write_json(self.manifest_path, self.intake_template())
        if not self.consent_path.exists():
            atomic_write_json(self.consent_path, self.consent_template())
        if not self.state_path.exists():
            atomic_write_json(self.state_path, self.default_state())
        guide = self.intake / "請先閱讀-Emma素材放置說明.txt"
        if not guide.exists():
            guide.write_text(self.intake_guide(), encoding="utf-8")
        self.core.initialize()
        return self.status()

    def intake_template(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-production-intake.v1",
            "identityId": "emma",
            "submittedBy": "",
            "submittedAt": "",
            "identityFiles": [
                {
                    "file": "identity/請填入檔名.jpg",
                    "kind": "face",
                    "angle": "front",
                    "expression": "neutral",
                    "clothing": "consistent-base-outfit",
                    "notes": "",
                }
            ],
            "voiceFiles": [
                {
                    "file": "voice/請填入檔名.wav",
                    "transcript": "請填入與錄音完全一致的逐字稿",
                    "language": "zh-TW",
                    "emotion": "neutral",
                    "notes": "",
                }
            ],
        }

    def consent_template(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-consent.v1",
            "identityId": "emma",
            "subjectLegalName": "",
            "rightsHolder": "",
            "consentGranted": False,
            "sourceOwnershipConfirmed": False,
            "permittedUses": [
                "identity-training",
                "voice-cloning",
                "synthetic-media",
                "commercial-content",
            ],
            "territory": "worldwide",
            "term": "until-revoked",
            "signedAt": "",
            "revocationContact": "",
            "evidenceFile": "",
            "notes": "",
        }

    def default_state(self) -> dict[str, Any]:
        return {
            "schema": "temple-ai-studio.emma-production-state.v1",
            "version": EMMA_PRODUCTION_VERSION,
            "identityId": "emma",
            "status": "WAITING_FOR_CEO_MATERIALS",
            "activeVersion": None,
            "identityActivated": False,
            "voiceActivated": False,
            "updatedAt": now_iso(),
        }

    def _sync_core_activation(
        self,
        identity_artifact: Path,
        identity_payload: dict[str, Any],
        voice_profile: Path,
        voice_payload: dict[str, Any],
        production_version: str,
    ) -> bool:
        profile = read_json(
            self.core.profile_path,
            self.core.default_identity_profile(),
        )
        identity_rules = dict(profile.get("identityRules", {}))
        identity_rules.update(
            {
                "trainingRequiresCeoDatasetApproval": False,
                "voiceCloningDisabledInThisPack": False,
                "modelFineTuningDisabledInThisPack": False,
                "realPersonVoiceCloningProhibited": True,
            }
        )
        activation = {
            "productionVersion": production_version,
            "identityActivated": True,
            "voiceActivated": True,
            "identityVersion": identity_payload.get("identityVersion", ""),
            "identityAdapter": str(Path(identity_artifact).resolve()),
            "voiceProfile": str(Path(voice_profile).resolve()),
            "voiceProfileId": voice_payload.get("profileId", ""),
        }
        permanent_identity = dict(profile.get("permanentIdentity", {}))
        for field in [
            "faceIdentity",
            "bodyIdentity",
            "bodyProportions",
            "skinTone",
            "facialGeometry",
        ]:
            value = dict(permanent_identity.get(field, {}))
            value["status"] = "synthetic-production-active"
            permanent_identity[field] = value
        desired = {
            "status": "production-active",
            "identityAdapter": str(Path(identity_artifact).resolve()),
            "canonicalVoiceProfile": voice_payload.get("profileId", ""),
            "identityRules": identity_rules,
            "permanentIdentity": permanent_identity,
            "productionActivation": activation,
        }
        changed = any(profile.get(key) != value for key, value in desired.items())
        if changed:
            profile.update(desired)
            profile["updatedAt"] = now_iso()
            atomic_write_json(self.core.profile_path, profile)
        return changed

    def intake_guide(self) -> str:
        return (
            "Temple AI Studio - Emma 正式素材匯入\n\n"
            "1. 身分照片放到 identity 資料夾，只放本人已授權素材。\n"
            "2. 聲音放到 voice 資料夾，格式必須是單聲道 PCM WAV。\n"
            "3. 在 emma-intake.json 列出每個檔案；聲音逐字稿必須與錄音完全一致。\n"
            "4. 完成 consent/emma-consent.json，並把簽署證明放進 consent 資料夾。\n"
            "5. 不要裁切、磨皮、加濾鏡、降噪過度或加入背景音樂。\n"
            "6. Temple AI Studio 會拒絕重複、模糊、過暗、過曝、削波或靜音過多的素材。\n"
        )

    def validate_consent(self) -> dict[str, Any]:
        consent = read_json(self.consent_path, {})
        evidence = self.consent_dir / str(consent.get("evidenceFile", ""))
        permitted = set(consent.get("permittedUses", []))
        checks = [
            {"name": "identity-id", "ok": consent.get("identityId") == "emma"},
            {"name": "subject-name", "ok": bool(str(consent.get("subjectLegalName", "")).strip())},
            {"name": "rights-holder", "ok": bool(str(consent.get("rightsHolder", "")).strip())},
            {"name": "consent-granted", "ok": consent.get("consentGranted") is True},
            {"name": "source-ownership", "ok": consent.get("sourceOwnershipConfirmed") is True},
            {"name": "permitted-uses", "ok": REQUIRED_CONSENT_USES.issubset(permitted)},
            {"name": "territory", "ok": bool(str(consent.get("territory", "")).strip())},
            {"name": "term", "ok": bool(str(consent.get("term", "")).strip())},
            {"name": "signed-at", "ok": bool(str(consent.get("signedAt", "")).strip())},
            {"name": "revocation-contact", "ok": bool(str(consent.get("revocationContact", "")).strip())},
            {
                "name": "signed-evidence",
                "ok": bool(consent.get("evidenceFile")) and evidence.is_file(),
                "path": str(evidence),
            },
        ]
        return {
            "schema": "temple-ai-studio.emma-consent-validation.v1",
            "overall": "PASS" if all(check["ok"] for check in checks) else "FAIL",
            "checks": checks,
        }

    def scan_intake(self, copy_files: bool = False) -> dict[str, Any]:
        self.initialize()
        manifest = read_json(self.manifest_path, {})
        consent = self.validate_consent()
        accepted_identity: list[dict[str, Any]] = []
        accepted_voice: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        exact_hashes: dict[str, str] = {}
        perceptual_hashes: list[tuple[str, str, str]] = []

        for item in manifest.get("identityFiles", []):
            relative = str(item.get("file", ""))
            source = (self.intake / relative).resolve()
            reason = self._safe_intake_path(source)
            if reason or not source.is_file() or source.suffix.lower() not in IMAGE_EXTENSIONS:
                rejected.append({"file": relative, "mediaType": "identity", "reason": reason or "missing-or-unsupported"})
                continue
            if item.get("kind") not in IDENTITY_KINDS:
                rejected.append({"file": relative, "mediaType": "identity", "reason": "invalid-identity-kind"})
                continue
            try:
                quality = analyze_identity_image(source)
            except (OSError, ValueError) as error:
                rejected.append({"file": relative, "mediaType": "identity", "reason": f"invalid-image:{error}"})
                continue
            duplicate = self._duplicate_reason(quality, exact_hashes, perceptual_hashes)
            if duplicate:
                rejected.append({"file": relative, "mediaType": "identity", "reason": duplicate, "quality": quality})
                continue
            exact_hashes[quality["sha256"]] = relative
            perceptual_hashes.append(
                (quality["perceptualHash"], quality["differenceHash"], relative)
            )
            record = {"file": relative, "source": str(source), "metadata": item, "quality": quality}
            if quality["overall"] == "PASS":
                accepted_identity.append(record)
            else:
                rejected.append({"file": relative, "mediaType": "identity", "reason": "quality-filter", "quality": quality})

        voice_seconds = 0.0
        for item in manifest.get("voiceFiles", []):
            relative = str(item.get("file", ""))
            source = (self.intake / relative).resolve()
            reason = self._safe_intake_path(source)
            if reason or not source.is_file() or source.suffix.lower() not in VOICE_EXTENSIONS:
                rejected.append({"file": relative, "mediaType": "voice", "reason": reason or "missing-or-unsupported"})
                continue
            transcript = str(item.get("transcript", "")).strip()
            if len(transcript) < 2:
                rejected.append({"file": relative, "mediaType": "voice", "reason": "transcript-required"})
                continue
            try:
                quality = analyze_voice_wav(source)
            except (OSError, ValueError, wave.Error) as error:
                rejected.append({"file": relative, "mediaType": "voice", "reason": f"invalid-wav:{error}"})
                continue
            duplicate = self._duplicate_reason(quality, exact_hashes, [])
            if duplicate:
                rejected.append({"file": relative, "mediaType": "voice", "reason": duplicate, "quality": quality})
                continue
            exact_hashes[quality["sha256"]] = relative
            record = {"file": relative, "source": str(source), "metadata": item, "quality": quality}
            if quality["overall"] == "PASS":
                accepted_voice.append(record)
                voice_seconds += quality["durationSeconds"]
            else:
                rejected.append({"file": relative, "mediaType": "voice", "reason": "quality-filter", "quality": quality})

        distribution = {
            kind: sum(1 for item in accepted_identity if item["metadata"].get("kind") == kind)
            for kind in sorted(IDENTITY_KINDS)
        }
        dataset_checks = [
            {
                "name": "identity-count",
                "ok": len(accepted_identity) >= MINIMUM_IDENTITY_IMAGES,
                "value": len(accepted_identity),
                "minimum": MINIMUM_IDENTITY_IMAGES,
                "recommended": RECOMMENDED_IDENTITY_IMAGES,
            },
            {
                "name": "identity-coverage",
                "ok": distribution["face"] >= 5
                and distribution["half-body"] >= 4
                and distribution["full-body"] >= 4
                and sum(distribution[kind] for kind in {"profile", "expression", "pose"}) >= 5,
                "value": distribution,
            },
            {
                "name": "voice-duration",
                "ok": voice_seconds >= MINIMUM_VOICE_SECONDS,
                "valueSeconds": round(voice_seconds, 3),
                "minimumSeconds": MINIMUM_VOICE_SECONDS,
                "recommendedSeconds": RECOMMENDED_VOICE_SECONDS,
            },
            {
                "name": "consent-and-license",
                "ok": consent["overall"] == "PASS",
            },
        ]
        report = {
            "schema": "temple-ai-studio.emma-production-intake-report.v1",
            "createdAt": now_iso(),
            "overall": "PASS" if all(check["ok"] for check in dataset_checks) else "FAIL",
            "consent": consent,
            "datasetChecks": dataset_checks,
            "acceptedIdentity": accepted_identity,
            "acceptedVoice": accepted_voice,
            "rejected": rejected,
            "summary": {
                "identityAccepted": len(accepted_identity),
                "voiceAccepted": len(accepted_voice),
                "voiceSeconds": round(voice_seconds, 3),
                "rejected": len(rejected),
                "identityDistribution": distribution,
            },
        }
        atomic_write_json(self.intake_report_path, report)
        if copy_files and report["overall"] == "PASS":
            self._materialize_dataset(report)
        return report

    def prepare_adapters(self) -> dict[str, Any]:
        report = self.scan_intake(copy_files=True)
        if report["overall"] != "PASS":
            raise RuntimeError("Emma dataset cannot be prepared until intake and consent validation pass.")
        identity = {
            "schema": "temple-ai-studio.emma-identity-adapter-preparation.v1",
            "createdAt": now_iso(),
            "identityId": "emma",
            "training": {
                "approach": "lora",
                "baseModel": "black-forest-labs/FLUX.2-klein-base-4B",
                "license": "Apache-2.0",
                "purpose": "Emma identity and body consistency",
                "datasetPath": str(self.accepted / "identity"),
                "outputPath": str(self.root / "artifacts" / "identity"),
                "triggerToken": "temple_emma",
                "requiredArtifact": "emma-flux2-klein-4b-lora.safetensors",
                "status": "READY_FOR_TRAINING",
            },
            "inference": {
                "primary": "black-forest-labs/FLUX.2-klein-4B",
                "immediateReferenceProvider": "Qwen-Image-Edit-2509",
                "requiredIdentityEvaluator": "OpenCV-SFace",
            },
            "datasetHashes": [item["quality"]["sha256"] for item in report["acceptedIdentity"]],
        }
        voice = {
            "schema": "temple-ai-studio.emma-voice-profile-preparation.v1",
            "createdAt": now_iso(),
            "identityId": "emma",
            "primary": {
                "engine": "Qwen3-TTS-12Hz-0.6B-Base",
                "license": "Apache-2.0",
                "mode": "zero-shot-clone-then-benchmark-finetune",
                "datasetPath": str(self.accepted / "voice"),
                "requiredArtifact": "emma-qwen3-tts-voice-profile.json",
                "status": "READY_FOR_VOICE_PROFILE",
            },
            "fallbackBenchmark": "Fun-CosyVoice3-0.5B",
            "requiredSpeakerEvaluator": "WavLM-Base-Plus-SV",
            "datasetHashes": [item["quality"]["sha256"] for item in report["acceptedVoice"]],
        }
        atomic_write_json(self.preparation / "identity-adapter-preparation.json", identity)
        atomic_write_json(self.preparation / "voice-profile-preparation.json", voice)
        return {"overall": "PASS", "identity": identity, "voice": voice}

    def activate_version(
        self,
        identity_artifact: Path,
        voice_profile: Path,
        validation_evidence: Path,
    ) -> dict[str, Any]:
        preparation = self.prepare_adapters()
        return self.activate_prepared_version(
            identity_artifact,
            voice_profile,
            validation_evidence,
            preparation,
        )

    def activate_prepared_version(
        self,
        identity_artifact: Path,
        voice_profile: Path,
        validation_evidence: Path,
        preparation: dict[str, Any],
    ) -> dict[str, Any]:
        """Activate a validated Emma package prepared by an approved intake path."""
        evidence = read_json(Path(validation_evidence), {})
        required_checks = {
            "identitySimilarity",
            "bodyConsistency",
            "voiceSimilarity",
            "voiceNaturalness",
            "commercialUsability",
        }
        evidence_checks = evidence.get("checks", {})
        checks = [
            {"name": "identity-artifact", "ok": Path(identity_artifact).is_file()},
            {"name": "voice-profile", "ok": Path(voice_profile).is_file()},
            {
                "name": "prepared-dataset",
                "ok": preparation.get("overall") == "PASS"
                and str(preparation.get("provenance", "")).lower() == "real-production",
            },
            {
                "name": "real-evaluators",
                "ok": evidence.get("identityEvaluator") == "opencv-sface"
                and evidence.get("voiceEvaluator") == "wavlm-base-plus-sv",
            },
            {
                "name": "no-mock-evidence",
                "ok": str(evidence.get("provenance", "")).lower() == "real-production",
            },
            {
                "name": "required-validation",
                "ok": required_checks.issubset(evidence_checks)
                and all(evidence_checks[name].get("passed") is True for name in required_checks),
            },
        ]
        if not all(check["ok"] for check in checks):
            return {"overall": "BLOCKED", "checks": checks}
        current = read_json(self.state_path, self.default_state())
        identity_payload = read_json(Path(identity_artifact), {})
        voice_payload = read_json(Path(voice_profile), {})
        active_record = read_json(
            self.versions / f"{current.get('activeVersion')}.json",
            {},
        )
        matching_active_version = (
            current.get("status") == "ACTIVE"
            and current.get("activeVersion")
            and active_record.get("identityArtifactSha256")
            == sha256_file(Path(identity_artifact))
            and active_record.get("voiceProfileSha256")
            == sha256_file(Path(voice_profile))
            and active_record.get("validationEvidenceSha256")
            == sha256_file(Path(validation_evidence))
        )
        if matching_active_version:
            core_changed = self._sync_core_activation(
                Path(identity_artifact),
                identity_payload,
                Path(voice_profile),
                voice_payload,
                current["activeVersion"],
            )
            if core_changed:
                self.core.create_identity_version(
                    f"Production activation state synchronized {current['activeVersion']}"
                )
            if not current.get("activationFinalized"):
                self.core.create_identity_version(
                    f"Production activation {current['activeVersion']}"
                )
                current["activationFinalized"] = True
                current["updatedAt"] = now_iso()
                atomic_write_json(self.state_path, current)
            return {
                "overall": "PASS",
                "version": active_record,
                "state": current,
                "idempotent": True,
            }
        version_number = len(list(self.versions.glob("emma-production-v*.json"))) + 1
        version = f"emma-production-v{version_number}"
        record = {
            "schema": "temple-ai-studio.emma-production-version.v1",
            "version": version,
            "createdAt": now_iso(),
            "identityArtifact": str(Path(identity_artifact).resolve()),
            "identityArtifactSha256": sha256_file(Path(identity_artifact)),
            "voiceProfile": str(Path(voice_profile).resolve()),
            "voiceProfileSha256": sha256_file(Path(voice_profile)),
            "validationEvidence": str(Path(validation_evidence).resolve()),
            "validationEvidenceSha256": sha256_file(Path(validation_evidence)),
            "preparation": preparation,
            "previousVersion": current.get("activeVersion"),
        }
        atomic_write_json(self.versions / f"{version}.json", record)
        self._sync_core_activation(
            Path(identity_artifact),
            identity_payload,
            Path(voice_profile),
            voice_payload,
            version,
        )
        self.core.create_identity_version(f"Production activation {version}")
        state = {
            **current,
            "status": "ACTIVE",
            "activeVersion": version,
            "identityActivated": True,
            "voiceActivated": True,
            "activeIdentityVersion": identity_payload.get(
                "identityVersion",
                current.get("activeIdentityVersion"),
            ),
            "activeVoiceProfile": voice_payload.get("profileId", ""),
            "activationFinalized": True,
            "updatedAt": now_iso(),
        }
        atomic_write_json(self.state_path, state)
        return {"overall": "PASS", "version": record, "state": state}

    def rollback(self, version: str, confirmation: str) -> dict[str, Any]:
        if confirmation != f"ROLLBACK {version}":
            raise PermissionError(f"Confirmation must be exactly: ROLLBACK {version}")
        record_path = self.versions / f"{version}.json"
        record = read_json(record_path, {})
        if not record:
            raise ValueError(f"Emma production version does not exist: {version}")
        identity_artifact = Path(record.get("identityArtifact", ""))
        voice_profile = Path(record.get("voiceProfile", ""))
        if (
            not identity_artifact.is_file()
            or not voice_profile.is_file()
            or sha256_file(identity_artifact) != record.get("identityArtifactSha256")
            or sha256_file(voice_profile) != record.get("voiceProfileSha256")
        ):
            raise RuntimeError(
                f"Emma production version {version} failed artifact integrity validation."
            )
        identity_payload = read_json(identity_artifact, {})
        voice_payload = read_json(voice_profile, {})
        current = read_json(self.state_path, self.default_state())
        rollback_record = {
            "id": f"rollback-{uuid.uuid4().hex[:10]}",
            "fromVersion": current.get("activeVersion"),
            "toVersion": version,
            "createdAt": now_iso(),
        }
        core_changed = self._sync_core_activation(
            identity_artifact,
            identity_payload,
            voice_profile,
            voice_payload,
            version,
        )
        if core_changed:
            self.core.create_identity_version(f"Production rollback to {version}")
        current["activeVersion"] = version
        current["status"] = "ACTIVE"
        current["identityActivated"] = True
        current["voiceActivated"] = True
        current["activeIdentityVersion"] = identity_payload.get(
            "identityVersion",
            current.get("activeIdentityVersion"),
        )
        current["activeVoiceProfile"] = voice_payload.get("profileId", "")
        current["activationFinalized"] = True
        current["lastRollback"] = rollback_record
        current["updatedAt"] = now_iso()
        atomic_write_json(self.state_path, current)
        return {
            "overall": "PASS",
            "rollback": rollback_record,
            "state": current,
        }

    def status(self) -> dict[str, Any]:
        state = read_json(self.state_path, self.default_state())
        report = read_json(self.intake_report_path, {})
        return {
            "schema": "temple-ai-studio.emma-production-status.v1",
            "version": EMMA_PRODUCTION_VERSION,
            "state": state,
            "intake": report.get("summary", {}),
            "intakeOverall": report.get("overall", "NOT_RUN"),
            "paths": {
                "root": str(self.root),
                "identityInbox": str(self.identity_inbox),
                "voiceInbox": str(self.voice_inbox),
                "consent": str(self.consent_path),
                "manifest": str(self.manifest_path),
                "report": str(self.intake_report_path),
            },
        }

    def _safe_intake_path(self, path: Path) -> str | None:
        try:
            path.relative_to(self.intake.resolve())
            return None
        except ValueError:
            return "path-outside-intake"

    @staticmethod
    def _duplicate_reason(
        quality: dict[str, Any],
        exact_hashes: dict[str, str],
        perceptual_hashes: list[tuple[str, str, str]],
    ) -> str | None:
        if quality["sha256"] in exact_hashes:
            return f"exact-duplicate:{exact_hashes[quality['sha256']]}"
        if quality.get("perceptualHash"):
            for known_hash, known_difference, known_file in perceptual_hashes:
                if (
                    hamming_hex(quality["perceptualHash"], known_hash) <= 2
                    and hamming_hex(quality["differenceHash"], known_difference) <= 2
                ):
                    return f"near-duplicate:{known_file}"
        return None

    def _materialize_dataset(self, report: dict[str, Any]) -> None:
        for category, items in [
            ("identity", report["acceptedIdentity"]),
            ("voice", report["acceptedVoice"]),
        ]:
            target_root = self.accepted / category
            target_root.mkdir(parents=True, exist_ok=True)
            for item in items:
                source = Path(item["source"])
                target = target_root / f"{item['quality']['sha256'][:12]}-{source.name}"
                if not target.exists():
                    shutil.copy2(source, target)
                metadata = {**item, "acceptedPath": str(target)}
                atomic_write_json(target.with_suffix(target.suffix + ".json"), metadata)
        for item in report.get("rejected", []):
            relative = item.get("file", "")
            source = (self.intake / relative).resolve()
            category = item.get("mediaType", "identity")
            if source.is_file() and self._safe_intake_path(source) is None:
                target = self.rejected / category / f"{uuid.uuid4().hex[:8]}-{source.name}"
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(source, target)
                atomic_write_json(target.with_suffix(target.suffix + ".json"), item)
