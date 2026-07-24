from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESTORE_CONFIRMATION = "RESTORE EMMA FINAL ACTIVATION"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return fallback or {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class FinalActivationBackupManager:
    """Backs up activated Emma state without raw intake, models, exports, or secrets."""

    FILES = {
        "emma/emma-production-state.json",
        "providers/providers.json",
        "providers/cost-ledger.json",
        "acceptance/final-acceptance-report.json",
        "acceptance/final-acceptance-dashboard.html",
    }
    DIRECTORIES = {
        "emma/versions",
        "emma/identity-adapters",
        "emma/voice-profiles",
        "emma/video-activation/canonical-video-v1/reports",
        "emma/video-activation/canonical-video-v1/voice/segments",
        "emma/video-activation/canonical-video-v1/validation",
        "avatar",
        "workflows",
    }
    ALLOWED_SUFFIXES = {
        ".json",
        ".html",
        ".txt",
        ".md",
        ".yaml",
        ".yml",
        ".wav",
    }

    def __init__(self, production_root: Path | str):
        self.root = Path(production_root).resolve()
        self.backup_root = self.root / "backups" / "final-activation"

    def selected_files(self) -> list[Path]:
        files = []
        for relative in sorted(self.FILES):
            path = self.root / relative
            if path.is_file():
                files.append(path)
        for relative in sorted(self.DIRECTORIES):
            directory = self.root / relative
            if not directory.is_dir():
                continue
            files.extend(
                path
                for path in sorted(directory.rglob("*"))
                if path.is_file()
                and path.suffix.lower() in self.ALLOWED_SUFFIXES
                and "secrets" not in {part.lower() for part in path.parts}
            )
        return list(dict.fromkeys(files))

    def create(self, label: str = "emma-final") -> dict[str, Any]:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive = self.backup_root / f"{label}-{stamp}.zip"
        files = self.selected_files()
        if not files:
            raise RuntimeError("No activated Emma production files were found to back up.")
        checksums = {
            path.relative_to(self.root).as_posix(): sha256_file(path)
            for path in files
        }
        manifest = {
            "schema": "temple-ai-studio.final-activation-backup.v1",
            "createdAt": now_iso(),
            "sourceRoot": str(self.root),
            "files": checksums,
            "privacy": {
                "rawIntakeExcluded": True,
                "modelsExcluded": True,
                "exportsExcluded": True,
                "secretsExcluded": True,
            },
        }
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for path in files:
                output.write(path, path.relative_to(self.root).as_posix())
            output.writestr(
                "BACKUP_MANIFEST.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
        result = {
            "schema": "temple-ai-studio.final-activation-backup-result.v1",
            "overall": "PASS",
            "archive": str(archive),
            "bytes": archive.stat().st_size,
            "fileCount": len(files),
            "manifest": manifest,
        }
        atomic_json(self.backup_root / f"{archive.stem}-report.json", result)
        return result

    def restore(
        self,
        archive: Path | str,
        target_root: Path | str,
        confirmation: str,
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        if confirmation != RESTORE_CONFIRMATION:
            raise PermissionError(f"Confirmation must be exactly: {RESTORE_CONFIRMATION}")
        archive = Path(archive).resolve()
        target = Path(target_root).resolve()
        if not archive.is_file():
            raise FileNotFoundError(str(archive))
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "r") as source:
            manifest = json.loads(source.read("BACKUP_MANIFEST.json").decode("utf-8"))
            restored = []
            for relative, expected_hash in manifest["files"].items():
                destination = (target / relative).resolve()
                try:
                    destination.relative_to(target)
                except ValueError as error:
                    raise RuntimeError(f"Unsafe backup member: {relative}") from error
                if destination.exists() and not allow_overwrite:
                    raise FileExistsError(
                        f"Restore will not overwrite without explicit permission: {destination}"
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source.open(relative) as input_file, destination.open("wb") as output_file:
                    while True:
                        block = input_file.read(1024 * 1024)
                        if not block:
                            break
                        output_file.write(block)
                actual = sha256_file(destination)
                if actual != expected_hash:
                    raise RuntimeError(f"Restored checksum mismatch: {relative}")
                restored.append(relative)
        validation = self.validate_restore(target, manifest)
        result = {
            "schema": "temple-ai-studio.final-activation-restore-result.v1",
            "overall": "PASS" if validation["overall"] == "PASS" else "FAIL",
            "archive": str(archive),
            "targetRoot": str(target),
            "restoredFiles": len(restored),
            "validation": validation,
        }
        atomic_json(target / "RESTORE_VALIDATION.json", result)
        return result

    @staticmethod
    def validate_restore(
        target: Path,
        backup_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        state = read_json(target / "emma" / "emma-production-state.json")
        profile_path = (
            target
            / "emma"
            / "voice-profiles"
            / "emma-canonical-video-voice-v1.json"
        )
        profile = read_json(profile_path)
        source_root = Path(backup_manifest["sourceRoot"]).resolve()

        def restored_equivalent(raw: str) -> Path:
            path = Path(raw).resolve()
            try:
                relative = path.relative_to(source_root)
            except ValueError:
                return path
            return target / relative

        reference_audio = restored_equivalent(profile.get("referenceAudio", ""))
        active_version = state.get("activeVersion")
        version = read_json(target / "emma" / "versions" / f"{active_version}.json")
        identity_artifact = restored_equivalent(version.get("identityArtifact", ""))
        checks = [
            {"name": "state-active", "ok": state.get("status") == "ACTIVE"},
            {"name": "identity-active", "ok": state.get("identityActivated") is True},
            {"name": "voice-active", "ok": state.get("voiceActivated") is True},
            {
                "name": "canonical-profile",
                "ok": profile.get("canonical") is True
                and profile.get("profileId") == "emma-canonical-video-voice-v1",
            },
            {
                "name": "reference-audio-restored",
                "ok": reference_audio.is_file() and reference_audio.stat().st_size > 44,
                "path": str(reference_audio),
            },
            {
                "name": "identity-artifact-restored",
                "ok": identity_artifact.is_file(),
                "path": str(identity_artifact),
            },
        ]
        return {
            "overall": "PASS" if all(item["ok"] for item in checks) else "FAIL",
            "checks": checks,
        }


__all__ = ["FinalActivationBackupManager", "RESTORE_CONFIRMATION"]
