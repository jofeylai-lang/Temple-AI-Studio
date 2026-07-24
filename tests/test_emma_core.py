from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from temple_ai_studio.emma_core import ASSET_CATEGORIES, PROVIDERS, EmmaCore
from temple_ai_studio.image_pipeline import run_image_pipeline
from temple_ai_studio.script_engine import generate_video_script_package


def make_emma_image(path: Path, rgb: tuple[int, int, int], label: str = "A") -> None:
    image = Image.new("RGB", (768, 1024), rgb)
    draw = ImageDraw.Draw(image)
    if label == "B":
        draw.rectangle((90, 120, 680, 360), fill=tuple(min(255, channel + 50) for channel in rgb))
        draw.ellipse((230, 515, 560, 930), fill=tuple(max(0, channel - 70) for channel in rgb))
        draw.line((80, 940, 690, 130), fill=(255, 255, 255), width=16)
    else:
        draw.ellipse((240, 150, 528, 438), fill=tuple(min(255, channel + 25) for channel in rgb))
        draw.rectangle((285, 455, 485, 860), fill=tuple(max(0, channel - 35) for channel in rgb))
        draw.text((360, 520), label, fill=(255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


class EmmaCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.core = EmmaCore(self.root)
        self.core.initialize()
        self.face = self.root / "source" / "emma-face.png"
        self.similar = self.root / "source" / "emma-similar.png"
        self.different = self.root / "source" / "different.png"
        make_emma_image(self.face, (216, 176, 150), "A")
        make_emma_image(self.similar, (218, 178, 152), "A")
        make_emma_image(self.different, (45, 90, 220), "B")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dataset_indexing_duplicate_detection_and_provider_selection(self) -> None:
        imported = self.core.import_dataset_item(self.face, "face", "front-face", approved_by="test")
        duplicate = self.core.import_dataset_item(self.face, "face", "front-face-duplicate", approved_by="test")
        selection = self.core.select_references("comfyui", require_emma=True)
        self.assertEqual(imported["overall"], "PASS")
        self.assertEqual(duplicate["overall"], "DUPLICATE")
        self.assertEqual(selection["overall"], "PASS")
        self.assertEqual(selection["references"][0]["referenceType"], "face")

    def test_all_provider_adapters_select_references(self) -> None:
        self.core.import_dataset_item(self.face, "face", "front-face", approved_by="test")
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                selection = self.core.select_references(provider, require_emma=True)
                self.assertEqual(selection["overall"], "PASS")
                self.assertIn("adapter", selection)

    def test_voice_metadata_and_asset_library_structure(self) -> None:
        voice = self.root / "source" / "emma-voice.wav"
        voice.write_bytes(b"RIFF0000WAVEfmt test voice data")
        imported = self.core.import_dataset_item(voice, "voice", "voice-reference", approved_by="test")
        status = self.core.status()
        library = self.core.get_context()["status"]
        self.assertEqual(imported["overall"], "PASS")
        self.assertEqual(status["referenceCount"], 1)
        self.assertGreaterEqual(library["assetCount"], 1)
        asset_library = self.core.default_asset_library()
        self.assertEqual(set(asset_library["categories"].keys()), set(ASSET_CATEGORIES))

    def test_identity_scoring_accepts_similar_and_rejects_different(self) -> None:
        self.core.import_dataset_item(self.face, "face", "front-face", approved_by="test")
        similar = self.core.evaluate_generation(self.similar, provider="openai", require_emma=True)
        different = self.core.evaluate_generation(self.different, provider="openai", require_emma=True)
        self.assertEqual(similar["overall"], "PASS")
        self.assertEqual(different["overall"], "FAIL")

    def test_version_create_and_rollback(self) -> None:
        version = self.core.create_identity_version("unit-test-version")
        rollback = self.core.rollback_identity_version("emma-v1")
        status = self.core.status()
        self.assertEqual(version["version"], "emma-v2")
        self.assertEqual(rollback["overall"], "PASS")
        self.assertEqual(status["identityVersion"], "emma-v1")

    def test_missing_references_block_explicit_emma_generation(self) -> None:
        product_image = self.root / "product.png"
        make_emma_image(product_image, (230, 210, 180), "P")
        product = {
            "id": "product-test",
            "name": "Temple Product",
            "category": "香氛商品",
            "description": "測試商品。",
            "sellingPoint": "測試賣點。",
            "spiritualInfo": "測試祝福。",
            "targetAudience": "測試顧客",
            "materials": [{"id": "m1", "fileName": "product.png", "path": str(product_image), "role": "main-product"}],
        }
        project = generate_video_script_package(product, {"requirement": "請讓 Emma 介紹商品。"}, "project-test")
        project["id"] = "project-test"
        project["projectDir"] = str(self.root / "project")
        project["scenes"][0]["visualDescription"] = "Emma looks at camera and presents the product."
        with self.assertRaises(RuntimeError):
            run_image_pipeline(project, product, Path(project["projectDir"]), emma_root=self.root)


if __name__ == "__main__":
    unittest.main()
