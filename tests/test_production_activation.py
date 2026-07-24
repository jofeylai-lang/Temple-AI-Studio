from __future__ import annotations

import json
import math
import random
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.commercial_acceptance import CommercialAcceptanceSystem, FinalReleaseManager
from temple_ai_studio.emma_production import EmmaProductionActivator, analyze_identity_image, analyze_voice_wav
from temple_ai_studio.provider_activation import ProviderActivationManager, detect_ffmpeg
from temple_ai_studio.production_workflow import (
    FFmpegCommercialRenderer,
    RealProductionWorkflow,
)
from temple_ai_studio.real_providers import (
    LocalCommandProductionClient,
    ProviderExecutionError,
)
from temple_ai_studio.secure_secrets import SecureSecretStore


def make_identity_image(path: Path, index: int) -> None:
    image = Image.new("RGB", (768, 1024), (140 + index * 3 % 80, 110, 90))
    draw = ImageDraw.Draw(image)
    generator = random.Random(index)
    for _ in range(220):
        x = generator.randrange(0, image.width - 20)
        y = generator.randrange(0, image.height - 20)
        width = generator.randrange(12, 150)
        height = generator.randrange(12, 180)
        color = (
            generator.randrange(20, 250),
            generator.randrange(20, 250),
            generator.randrange(20, 250),
        )
        draw.rectangle((x, y, min(image.width, x + width), min(image.height, y + height)), fill=color)
    draw.ellipse((220, 140, 560, 480), outline=(255, 255, 255), width=12)
    draw.text((40 + index * 7, 600 + index * 5), f"EMMA-{index}", fill=(255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=95)


def make_voice(path: Path, frequency: float, seconds: int = 30) -> None:
    sample_rate = 24000
    one_second = [
        int(math.sin(2 * math.pi * frequency * index / sample_rate) * 6000)
        for index in range(sample_rate)
    ]
    frames = struct.pack("<" + "h" * len(one_second), *one_second) * seconds
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frames)


class ProductionActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.production = self.root / "production"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_media_quality_analyzers(self) -> None:
        image = self.root / "identity.jpg"
        voice = self.root / "voice.wav"
        make_identity_image(image, 1)
        make_voice(voice, 180)
        self.assertEqual(analyze_identity_image(image)["overall"], "PASS")
        self.assertEqual(analyze_voice_wav(voice)["overall"], "PASS")

    def test_complete_emma_intake_and_adapter_preparation(self) -> None:
        activator = EmmaProductionActivator(self.project, self.production / "emma")
        activator.initialize()
        evidence = activator.consent_dir / "signed-consent.txt"
        evidence.write_text("signed", encoding="utf-8")
        consent = activator.consent_template()
        consent.update(
            {
                "subjectLegalName": "Emma Test",
                "rightsHolder": "Emma Test",
                "consentGranted": True,
                "sourceOwnershipConfirmed": True,
                "signedAt": "2026-07-24",
                "revocationContact": "owner@example.invalid",
                "evidenceFile": evidence.name,
            }
        )
        activator.consent_path.write_text(json.dumps(consent), encoding="utf-8")

        identity_files = []
        kinds = (
            ["face"] * 5
            + ["half-body"] * 4
            + ["full-body"] * 4
            + ["profile"] * 3
            + ["expression"] * 2
            + ["pose"] * 2
        )
        for index, kind in enumerate(kinds):
            path = activator.identity_inbox / f"identity-{index}.jpg"
            make_identity_image(path, index)
            identity_files.append(
                {
                    "file": f"identity/{path.name}",
                    "kind": kind,
                    "angle": "front" if kind == "face" else "varied",
                    "expression": "neutral",
                    "clothing": "base",
                }
            )
        voice_files = []
        for index in range(20):
            path = activator.voice_inbox / f"voice-{index}.wav"
            make_voice(path, 150 + index * 7)
            voice_files.append(
                {
                    "file": f"voice/{path.name}",
                    "transcript": f"這是 Emma 正式語音素材第 {index + 1} 段。",
                    "language": "zh-TW",
                    "emotion": "neutral",
                }
            )
        manifest = activator.intake_template()
        manifest.update(
            {
                "submittedBy": "CEO",
                "submittedAt": "2026-07-24",
                "identityFiles": identity_files,
                "voiceFiles": voice_files,
            }
        )
        activator.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        report = activator.scan_intake(copy_files=True)
        self.assertEqual(report["overall"], "PASS")
        self.assertEqual(report["summary"]["identityAccepted"], 20)
        self.assertGreaterEqual(report["summary"]["voiceSeconds"], 600)
        preparation = activator.prepare_adapters()
        self.assertEqual(preparation["overall"], "PASS")
        self.assertEqual(
            preparation["identity"]["training"]["baseModel"],
            "black-forest-labs/FLUX.2-klein-base-4B",
        )
        self.assertEqual(
            preparation["voice"]["primary"]["engine"],
            "Qwen3-TTS-12Hz-0.6B-Base",
        )

    def test_provider_billing_is_locked_and_emergency_stop_is_immediate(self) -> None:
        manager = ProviderActivationManager(self.production / "providers")
        manager.initialize()
        with self.assertRaises(PermissionError):
            manager.configure_provider("openai-paid", {"enabled": True})
        manager.authorize_billing("CEO-TEST-1", 1000, 100)
        manager.configure_provider("openai-paid", {"enabled": True})
        stopped = manager.emergency_disable_billing()
        self.assertFalse(stopped["billingEnabled"])
        self.assertIn("openai-paid", stopped["disabledProviders"])
        self.assertFalse(manager.provider("openai-paid")["enabled"])

    def test_application_owned_provider_entry_points_follow_current_install(self) -> None:
        manager = ProviderActivationManager(self.production / "providers")
        manager.initialize()
        registry = manager.load()
        qwen = next(
            item for item in registry["providers"] if item["id"] == "qwen3-tts-local"
        )
        musetalk = next(
            item for item in registry["providers"] if item["id"] == "musetalk-local"
        )
        qwen["workerPath"] = r"D:\obsolete-development-copy\qwen3_tts_worker.py"
        musetalk["entryPoint"] = r"D:\obsolete-development-copy\musetalk_worker.py"
        manager.save(registry)

        rebound = manager.load()
        defaults = {
            item["id"]: item for item in manager.defaults()["providers"]
        }
        rebound_by_id = {item["id"]: item for item in rebound["providers"]}
        self.assertEqual(
            rebound_by_id["qwen3-tts-local"]["workerPath"],
            defaults["qwen3-tts-local"]["workerPath"],
        )
        self.assertEqual(
            rebound_by_id["musetalk-local"]["entryPoint"],
            defaults["musetalk-local"]["entryPoint"],
        )

    def test_generic_comfy_host_cannot_be_selected_as_generation_provider(self) -> None:
        manager = ProviderActivationManager(self.production / "providers")
        manager.initialize()
        registry = json.loads(manager.registry_path.read_text(encoding="utf-8"))
        comfy = next(
            item for item in registry["providers"] if item["id"] == "comfyui-local"
        )
        comfy["capabilities"] = ["image", "video", "lip-sync"]
        manager.registry_path.write_text(
            json.dumps(registry, ensure_ascii=False),
            encoding="utf-8",
        )
        health = {
            "schema": "temple-ai-studio.provider-health.v1",
            "providers": {
                "comfyui-local": {"overall": "PASS"},
            },
        }
        manager.health_path.write_text(json.dumps(health), encoding="utf-8")
        self.assertEqual(manager.provider("comfyui-local")["capabilities"], ["workflow-host"])
        selection = manager.select("image")
        self.assertIsNone(selection["selected"])
        self.assertTrue(
            any(
                item["providerId"] == "comfyui-local"
                and item["reason"] == "capability-not-supported"
                for item in selection["rejected"]
            )
        )
        wan = manager.provider("wan22-ti2v-local")
        self.assertEqual(wan["licensePolicy"], "apache-2.0")
        self.assertEqual(wan["generation"]["maxFrames"], 49)

    def test_real_production_preflight_blocks_missing_external_assets(self) -> None:
        workflow = RealProductionWorkflow(self.project, self.production)
        report = workflow.preflight(run_health=False)
        self.assertEqual(report["overall"], "BLOCKED")
        codes = {item["code"] for item in report["blockers"]}
        self.assertIn("emma-identity-not-active", codes)
        self.assertIn("emma-voice-not-active", codes)
        self.assertIn("provider-unavailable:image", codes)

    def test_requested_research_requires_real_source_evidence(self) -> None:
        workflow = RealProductionWorkflow(self.project, self.production)
        with self.assertRaises(ProviderExecutionError):
            workflow._research_evidence({"researchRequired": True})
        evidence = self.production / "research.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(
            json.dumps(
                {
                    "provenance": "real-production",
                    "providerId": "temple-knowledge-local",
                    "providerKind": "local-library",
                    "sources": [
                        {
                            "title": "Temple 商品資料",
                            "source": "local://product-record",
                            "finding": "商品材質與用途已由品牌資料確認。",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = workflow._research_evidence(
            {"researchRequired": True, "researchEvidence": str(evidence)}
        )
        self.assertEqual(result["provenance"], "real-production")
        self.assertEqual(len(result["sources"]), 1)

    def test_approved_local_command_descriptor_executes_without_shell(self) -> None:
        worker = self.root / "worker.py"
        output = self.root / "command-output.txt"
        worker.write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "Path(sys.argv[1]).write_text('real-output', encoding='utf-8')\n",
            encoding="utf-8",
        )
        descriptor = self.root / "descriptor.json"
        descriptor.write_text(
            json.dumps(
                {
                    "id": "unit-real-command",
                    "version": "1.0.0",
                    "providerId": "unit-local",
                    "productionReady": True,
                    "requiredBindings": ["output"],
                    "allowedExecutableRoots": [str(Path(sys.executable).parent)],
                    "command": [sys.executable, str(worker), "{output}"],
                    "outputs": [{"mediaType": "file", "path": "{output}"}],
                }
            ),
            encoding="utf-8",
        )
        result = LocalCommandProductionClient().run_descriptor(
            descriptor,
            {"output": output},
            self.root / "command-run",
        )
        self.assertEqual(result["provenance"], "real-production")
        self.assertEqual(output.read_text(encoding="utf-8"), "real-output")

    def test_ffmpeg_commercial_renderer_creates_playable_mp4_with_subtitles(self) -> None:
        ffmpeg = detect_ffmpeg()
        if not Path(ffmpeg).is_file():
            self.skipTest("FFmpeg is not installed")
        clip = self.root / "source.mp4"
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=360x640:d=1",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-metadata",
                "comment=temple-private-prompt",
                str(clip),
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1000:])
        rendered = FFmpegCommercialRenderer(ffmpeg).finalize(
            [clip],
            [{"duration": 1, "subtitle": "神殿商品測試"}],
            self.root / "rendered",
            "9:16",
        )
        self.assertEqual(rendered["media"]["overall"], "PASS")
        rendered_path = Path(rendered["output"])
        self.assertTrue(rendered_path.is_file())
        metadata = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", str(rendered_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertNotIn("temple-private-prompt", metadata.stderr)

    @unittest.skipUnless(sys.platform == "win32", "Windows DPAPI test")
    def test_dpapi_secret_store_round_trip(self) -> None:
        store = SecureSecretStore(self.production / "secrets")
        store.initialize()
        store.put("unit-secret", "not-plaintext")
        self.assertEqual(store.get("unit-secret"), "not-plaintext")
        raw = (self.production / "secrets" / "unit-secret.dpapi").read_bytes()
        self.assertNotIn(b"not-plaintext", raw)

    def test_commercial_acceptance_rejects_mock_and_release_stays_locked(self) -> None:
        system = CommercialAcceptanceSystem(self.project, self.production)
        system.initialize()
        run_dir = system.runs_root / "mock-run"
        run_dir.mkdir(parents=True)
        manifest = {
            "runId": "mock-run",
            "scenarioType": "product-introduction",
            "requestLanguage": "zh-TW",
            "stages": {
                name: {
                    "status": "PASS",
                    "provenance": "mock" if name in {"image", "video", "voice", "lip-sync"} else "real-production",
                    "providerKind": "mock" if name in {"image", "video", "voice", "lip-sync"} else "local",
                    "providerId": "comfyui-local",
                }
                for name in [
                    "request",
                    "research",
                    "script",
                    "storyboard",
                    "emma",
                    "image",
                    "video",
                    "voice",
                    "lip-sync",
                    "subtitle",
                    "editing",
                    "quality",
                    "repair",
                    "export",
                ]
            },
            "qualityScores": {},
            "exportPath": "missing.mp4",
        }
        manifest_path = run_dir / "commercial-run.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        report = system.evaluate([manifest_path])
        self.assertEqual(report["overall"], "BLOCKED")
        self.assertTrue(
            any(
                error.startswith("non-production-provenance")
                for error in report["runs"][0]["errors"]
            )
        )
        with self.assertRaises(PermissionError):
            FinalReleaseManager(self.project, self.production).create_release("1.0.0")


if __name__ == "__main__":
    unittest.main()
